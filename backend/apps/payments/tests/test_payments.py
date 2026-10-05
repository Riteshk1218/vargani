from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from django.db import DatabaseError, transaction

from apps.contributions.models import Contribution, ContributionType
from apps.events.models import Event, EventParticipant
from apps.funds.models import Fund
from apps.organizations.models import FinancialYear
from apps.payments.models import Payment
from apps.people.models import Person
from apps.receipts.models import Receipt, ReceiptSeries

pytestmark = pytest.mark.django_db

IST = ZoneInfo("Asia/Kolkata")


@pytest.fixture
def setup(make_org, client_for):
    org = make_org("Shivaji Nagar Mandal")
    fy = FinancialYear.objects.get(organization=org)
    event = Event.objects.create(
        organization=org,
        financial_year=fy,
        name="Ganesh Chaturthi 2027",
        code="GC",
        start_date=date(2027, 4, 1),
        end_date=date(2028, 3, 31),
        thank_you_message="Ganpati Bappa Morya!",
    )
    fund = Fund.objects.create(organization=org, event=event, name="Utsav Fund")
    monthly = ContributionType.objects.create(
        organization=org, event=event, fund=fund, name="Monthly Vargani", kind="recurring_monthly"
    )
    donation = ContributionType.objects.create(organization=org, event=event, fund=fund, name="Donation")
    ritesh = Person.objects.create(organization=org, full_name="Ritesh Patil", mobile="+919812345678")
    admin = client_for(org.admin_user, org)
    return type(
        "S",
        (),
        {
            "org": org,
            "fy": fy,
            "event": event,
            "fund": fund,
            "monthly": monthly,
            "donation": donation,
            "ritesh": ritesh,
            "admin": admin,
        },
    )


def collect(client, s, lines, *, payer=None, mode="cash", url="/api/v1/payments/", headers=None, **extra):
    payload = {
        "event": str(s.event.pk),
        "payer": str((payer or s.ritesh).pk),
        "mode": mode,
        "lines": lines,
        **extra,
    }
    return client.post(url, payload, format="json", **(headers or {}))


def month_line(s, month, amount):
    return {"contribution_type": str(s.monthly.pk), "period_month": month, "amount": amount}


def test_ritesh_example_flexible_monthly_amounts(setup):
    s = setup
    for month, amount in [("2027-04-01", "500"), ("2027-05-01", "700"), ("2027-06-01", "1000"), ("2027-07-01", "400")]:
        response = collect(s.admin, s, [month_line(s, month, amount)])
        assert response.status_code == 201, response.data
    # Two payments in one month (₹300 + ₹200) are allowed.
    assert collect(s.admin, s, [month_line(s, "2027-08-01", "300")]).status_code == 201
    assert collect(s.admin, s, [month_line(s, "2027-08-15", "200")]).status_code == 201

    lines = Contribution.objects.filter(person=s.ritesh, status="confirmed")
    assert sum(line.amount for line in lines) == Decimal("3100.00")
    assert sum(line.amount for line in lines if line.period_month < date(2027, 8, 1)) == Decimal("2600.00")
    assert lines.filter(period_month=date(2027, 8, 1)).count() == 2  # 15th normalised to the 1st

    numbers = list(Receipt.objects.order_by("sequence").values_list("receipt_number", flat=True))
    assert numbers == [f"GC-2027-{n:05d}" for n in range(1, 7)]

    summary = s.admin.get(f"/api/v1/contributions/summary/?event={s.event.pk}").data
    assert summary["collected"] == "3100.00" and summary["contributors"] == 1 and summary["payments"] == 6
    assert summary["by_mode"] == [{"mode": "cash", "total": "3100.00", "count": 6}]
    assert summary["by_fund"][0]["name"] == "Utsav Fund"


def test_one_payment_can_cover_several_months_and_types(setup):
    s = setup
    response = collect(
        s.admin,
        s,
        [
            month_line(s, "2027-09-01", "500"),
            month_line(s, "2027-10-01", "500"),
            {"contribution_type": str(s.donation.pk), "amount": "251", "period_month": "2027-10-01"},
        ],
        mode="upi",
        reference_number="UPI123",
        amount="1251.00",
    )
    assert response.status_code == 201, response.data
    data = response.data
    assert data["amount"] == "1251.00" and len(data["lines"]) == 3
    assert data["receipt"]["receipt_number"] == "GC-2027-00001"
    donation_line = next(line for line in data["lines"] if str(line["contribution_type"]) == str(s.donation.pk))
    assert donation_line["period_month"] is None  # one-time types ignore the month
    receipt = Receipt.objects.get()
    assert receipt.snapshot["total"] == "1251.00" and len(receipt.snapshot["lines"]) == 3
    assert receipt.snapshot["thank_you_message"] == "Ganpati Bappa Morya!"


def test_receipt_snapshot_does_not_change_when_person_is_renamed(setup):
    s = setup
    collect(s.admin, s, [month_line(s, "2027-04-01", "500")])
    s.admin.patch(f"/api/v1/people/{s.ritesh.pk}/", {"full_name": "Ritesh S. Patil"}, format="json")
    receipt = s.admin.get("/api/v1/receipts/").data["results"][0]
    assert receipt["snapshot"]["person"]["name"] == "Ritesh Patil"
    assert receipt["payer_name"] == "Ritesh S. Patil"


@pytest.mark.parametrize(
    "change,field",
    [
        ({"amount": "999"}, "amount"),
        ({"lines": "no-month"}, "lines"),
        ({"mode": "cheque"}, "reference_number"),
        ({"mode": "online"}, "mode"),
        ({"lines": []}, "lines"),
        ({"lines": "zero"}, "lines"),
        ({"paid_at": "future"}, "paid_at"),
    ],
)
def test_validation(setup, change, field):
    s = setup
    lines = [month_line(s, "2027-04-01", "500")]
    extra = dict(change)
    if extra.get("lines") == "no-month":
        extra["lines"] = [{"contribution_type": str(s.monthly.pk), "amount": "500"}]
    elif extra.get("lines") == "zero":
        extra["lines"] = [month_line(s, "2027-04-01", "0")]
    if extra.get("paid_at") == "future":
        extra["paid_at"] = (datetime.now(IST) + timedelta(days=2)).isoformat()
    payload_lines = extra.pop("lines", lines)
    response = collect(s.admin, s, payload_lines, **extra)
    assert response.status_code == 400, response.data
    assert field in response.data["error"]["details"]
    assert Payment.objects.count() == 0 and Receipt.objects.count() == 0


def test_type_from_another_event_is_rejected(setup):
    s = setup
    other = Event.objects.create(organization=s.org, financial_year=s.fy, name="Navratri", code="NV")
    other_type = ContributionType.objects.create(organization=s.org, event=other, name="Garba Pass")
    response = collect(s.admin, s, [{"contribution_type": str(other_type.pk), "amount": "100"}])
    assert response.status_code == 400
    assert "lines" in response.data["error"]["details"]


def test_closed_event_refuses_collections(setup):
    s = setup
    s.admin.post(f"/api/v1/events/{s.event.pk}/close/")
    response = collect(s.admin, s, [month_line(s, "2027-04-01", "500")])
    assert response.status_code == 422


def test_idempotency_key_prevents_double_entry(setup):
    s = setup
    lines = [month_line(s, "2027-04-01", "500")]
    first = collect(s.admin, s, lines, headers={"HTTP_IDEMPOTENCY_KEY": "abc-1"})
    again = collect(s.admin, s, lines, headers={"HTTP_IDEMPOTENCY_KEY": "abc-1"})
    assert first.status_code == 201 and again.status_code == 200
    assert first.data["id"] == again.data["id"]
    assert Payment.objects.count() == 1 and Receipt.objects.count() == 1


def test_pending_cheque_then_confirm_issues_receipt(setup):
    s = setup
    response = collect(
        s.admin, s, [month_line(s, "2027-04-01", "500")], mode="cheque", reference_number="000123", status="pending"
    )
    assert response.status_code == 201
    assert response.data["receipt"] is None and response.data["lines"][0]["status"] == "pending"
    summary = s.admin.get(f"/api/v1/contributions/summary/?event={s.event.pk}").data
    assert summary["collected"] == "0.00"

    confirmed = s.admin.post(f"/api/v1/payments/{response.data['id']}/confirm/")
    assert confirmed.status_code == 200
    assert confirmed.data["status"] == "successful" and confirmed.data["receipt"]["receipt_number"] == "GC-2027-00001"
    assert s.admin.post(f"/api/v1/payments/{response.data['id']}/cancel/").status_code == 409


def test_cancel_pending_payment_keeps_record(setup):
    s = setup
    response = collect(
        s.admin, s, [month_line(s, "2027-04-01", "500")], mode="cheque", reference_number="9", status="pending"
    )
    cancelled = s.admin.post(f"/api/v1/payments/{response.data['id']}/cancel/", {"reason": "Wrong person"})
    assert cancelled.status_code == 200 and cancelled.data["status"] == "cancelled"
    assert cancelled.data["lines"][0]["status"] == "cancelled"
    assert Payment.objects.filter(pk=response.data["id"]).exists()
    assert Receipt.objects.count() == 0


def test_only_notes_are_editable(setup):
    s = setup
    payment_id = collect(s.admin, s, [month_line(s, "2027-04-01", "500")]).data["id"]
    response = s.admin.patch(f"/api/v1/payments/{payment_id}/", {"notes": "Paid at gate", "amount": "1"}, format="json")
    assert response.status_code == 200
    assert response.data["notes"] == "Paid at gate" and response.data["amount"] == "500.00"


def test_money_rows_cannot_be_deleted_or_rewritten(setup):
    s = setup
    payment_id = collect(s.admin, s, [month_line(s, "2027-04-01", "500")]).data["id"]
    for url in (f"/api/v1/payments/{payment_id}/", f"/api/v1/receipts/{Receipt.objects.get().pk}/"):
        assert s.admin.delete(url).status_code == 405

    checks = [
        lambda: Payment.objects.filter(pk=payment_id).delete(),
        lambda: Contribution.objects.all().delete(),
        lambda: Receipt.objects.all().delete(),
        lambda: ReceiptSeries.objects.all().delete(),
        lambda: Payment.objects.filter(pk=payment_id).update(amount=1),
        lambda: Contribution.objects.all().update(amount=1),
        lambda: Receipt.objects.all().update(receipt_number="GC-2027-99999"),
        lambda: Receipt.objects.all().update(snapshot={}),
        lambda: ReceiptSeries.objects.all().update(next_number=1),
    ]
    for check in checks:
        with pytest.raises(DatabaseError), transaction.atomic():
            check()
    assert Payment.objects.get(pk=payment_id).amount == Decimal("500.00")


def test_collector_needs_permission_setting_and_sees_only_own(setup, add_member, client_for):
    s = setup
    karyakarta = client_for(add_member(s.org, "collector"), s.org)
    other = client_for(add_member(s.org, "collector"), s.org)
    lines = [month_line(s, "2027-04-01", "500")]
    assert collect(karyakarta, s, lines, url="/api/v1/collections/").status_code == 403
    assert karyakarta.get("/api/v1/people/").data["count"] == 0

    s.org.settings = {"allow_unassigned_collection": True}
    s.org.save()
    assert karyakarta.get("/api/v1/people/").data["count"] == 1
    mine = collect(karyakarta, s, lines, url="/api/v1/collections/")
    assert mine.status_code == 201, mine.data
    assert mine.data["collector_name"]
    collect(s.admin, s, [month_line(s, "2027-05-01", "700")])

    assert [p["id"] for p in karyakarta.get("/api/v1/payments/").data["results"]] == [mine.data["id"]]
    assert other.get("/api/v1/payments/").data["count"] == 0
    assert other.get(f"/api/v1/payments/{mine.data['id']}/").status_code == 404
    assert karyakarta.get("/api/v1/receipts/").data["count"] == 1
    assert karyakarta.get("/api/v1/contributions/").data["count"] == 1
    summary = karyakarta.get(f"/api/v1/contributions/summary/?event={s.event.pk}").data
    assert summary["collected"] == "500.00"
    # Collectors cannot cancel and never see the financial dashboard.
    assert karyakarta.post(f"/api/v1/payments/{mine.data['id']}/cancel/").status_code == 403
    assert karyakarta.get("/api/v1/dashboard/summary/").data["financial"] is None


@pytest.mark.parametrize("role", ["volunteer", "member", "secretary"])
def test_roles_without_collection_rights(setup, add_member, client_for, role):
    s = setup
    s.org.settings = {"allow_unassigned_collection": True}
    s.org.save()
    client = client_for(add_member(s.org, role), s.org)
    assert collect(client, s, [month_line(s, "2027-04-01", "500")]).status_code == 403


def test_dashboard_financial_totals(setup):
    s = setup
    s.event.target_amount = Decimal("100000")
    s.event.save()
    collect(s.admin, s, [month_line(s, "2027-04-01", "500")])
    collect(s.admin, s, [month_line(s, "2027-05-01", "700")], mode="upi")
    data = s.admin.get(f"/api/v1/dashboard/summary/?event={s.event.pk}").data["financial"]
    assert data["collected"] == "1200.00" and data["target_amount"] == "100000.00"
    assert data["balance"] == "1200.00" and data["expenses"] == "0.00"
    assert {m["mode"]: m["total"] for m in data["by_mode"]} == {"cash": "500.00", "upi": "700.00"}
    assert data["recent_payments"][0]["receipt_number"].startswith("GC-2027-")
    # Without an event the dashboard covers the current financial year.
    assert s.admin.get("/api/v1/dashboard/summary/").data["financial"]["collected"] == "1200.00"


def test_outstanding_for_mandatory_type(setup):
    s = setup
    fee = ContributionType.objects.create(
        organization=s.org, event=s.event, name="Membership Fee", is_mandatory=True, target_amount=Decimal("1000")
    )
    asha = Person.objects.create(organization=s.org, full_name="Asha Kale")
    for person in (s.ritesh, asha):
        EventParticipant.objects.create(organization=s.org, event=s.event, person=person)
    collect(s.admin, s, [{"contribution_type": str(fee.pk), "amount": "600"}])
    data = s.admin.get(f"/api/v1/contribution-types/{fee.pk}/outstanding/").data
    assert data["total_expected"] == "2000.00" and data["total_paid"] == "600.00" and data["total_due"] == "1400.00"
    assert [(r["person_name"], r["due"]) for r in data["results"]] == [
        ("Asha Kale", "1000.00"),
        ("Ritesh Patil", "400.00"),
    ]
    assert s.admin.get(f"/api/v1/contribution-types/{s.donation.pk}/outstanding/").status_code == 422


def test_funds_and_types_api(setup):
    s = setup
    response = s.admin.post("/api/v1/funds/", {"event": str(s.event.pk), "name": "Annadan"}, format="json")
    assert response.status_code == 201
    assert (
        s.admin.post("/api/v1/funds/", {"event": str(s.event.pk), "name": "annadan"}, format="json").status_code == 400
    )
    payload = {"event": str(s.event.pk), "name": "Sponsor", "suggested_min": "5000", "suggested_max": "1000"}
    assert s.admin.post("/api/v1/contribution-types/", payload, format="json").status_code == 400
    payload = {"event": str(s.event.pk), "name": "Sponsor", "is_mandatory": True}
    assert s.admin.post("/api/v1/contribution-types/", payload, format="json").status_code == 400
    collect(s.admin, s, [month_line(s, "2027-04-01", "500")])
    response = s.admin.patch(f"/api/v1/contribution-types/{s.monthly.pk}/", {"kind": "one_time"}, format="json")
    assert response.status_code == 400
    archived = s.admin.patch(f"/api/v1/contribution-types/{s.monthly.pk}/", {"is_active": False}, format="json")
    assert archived.status_code == 200
    assert collect(s.admin, s, [month_line(s, "2027-05-01", "500")]).status_code == 400
