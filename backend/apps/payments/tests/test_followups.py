# ruff: noqa: F811
"""Door-to-door follow-ups: one pavti per house, updated on later visits instead of making a new one."""

from datetime import timedelta
from decimal import Decimal

import pytest

from apps.contributions.models import Contribution
from apps.payments import followups
from apps.payments.models import Payment
from apps.receipts.models import Receipt

from .test_payments import collect, setup  # noqa: F401

pytestmark = pytest.mark.django_db


def donation(s, amount):
    return {"contribution_type": str(s.donation.pk), "amount": amount}


def today(s):
    return followups.org_today(s.org)


def unpaid_pavti(s, amount="1001", received="0", follow_up=None):
    follow_up = follow_up or today(s) + timedelta(days=2)
    response = collect(s.admin, s, [donation(s, amount)], received=received, follow_up_on=follow_up.isoformat())
    assert response.status_code == 201, response.data
    return response.data


def test_unpaid_pavti_keeps_its_follow_up_date(setup):
    s = setup
    data = unpaid_pavti(s)
    assert data["pavti_status"] == "unpaid"
    assert data["balance_due"] == "1001.00"
    assert data["follow_up_on"] == (today(s) + timedelta(days=2)).isoformat()
    assert data["follow_up_state"] == "upcoming"
    part = unpaid_pavti(s, received="500")
    assert part["pavti_status"] == "partly_paid" and part["balance_due"] == "501.00"


def test_fully_paid_collection_has_no_follow_up(setup):
    s = setup
    response = collect(s.admin, s, [donation(s, "500")], follow_up_on=today(s).isoformat())
    assert response.status_code == 201
    assert response.data["pavti_status"] == "paid" and response.data["follow_up_on"] is None


def test_follow_up_date_cannot_be_in_the_past(setup):
    s = setup
    yesterday = (today(s) - timedelta(days=1)).isoformat()
    response = collect(s.admin, s, [donation(s, "500")], received="0", follow_up_on=yesterday)
    assert response.status_code == 400


def test_later_visit_updates_the_same_pavti(setup):
    s = setup
    data = unpaid_pavti(s)
    receipt = Receipt.objects.get(payment_id=data["id"])
    receipts_before = Receipt.objects.count()

    # Nobody home: only the date moves.
    later = (today(s) + timedelta(days=5)).isoformat()
    moved = s.admin.post(f"/api/v1/payments/{data['id']}/visit/", {"follow_up_on": later}, format="json")
    assert moved.status_code == 200, moved.data
    assert moved.data["follow_up_on"] == later and moved.data["amount"] == "0.00"

    # Part paid by UPI on the next visit, same pavti.
    part = s.admin.post(
        f"/api/v1/payments/{data['id']}/visit/",
        {"received": "600", "mode": "upi", "follow_up_on": later},
        format="json",
    )
    assert part.status_code == 200, part.data
    assert part.data["amount"] == "600.00" and part.data["mode"] == "upi"
    assert part.data["pavti_status"] == "partly_paid" and part.data["balance_due"] == "401.00"
    receipt.refresh_from_db()
    assert receipt.snapshot["total"] == "600.00" and receipt.snapshot["balance_total"] == "401.00"

    # Rest paid: pavti is paid and the follow-up date is cleared.
    rest = s.admin.post(f"/api/v1/payments/{data['id']}/visit/", {"received": "401"}, format="json")
    assert rest.status_code == 200, rest.data
    assert rest.data["pavti_status"] == "paid" and rest.data["follow_up_on"] is None
    assert Receipt.objects.count() == receipts_before
    receipt.refresh_from_db()
    assert receipt.receipt_number == Receipt.objects.get(payment_id=data["id"]).receipt_number
    assert receipt.snapshot["total"] == "1001.00" and receipt.snapshot["balance_total"] == "0.00"
    assert Payment.objects.get(pk=data["id"]).amount == Decimal("1001")
    assert sum(c.amount for c in Contribution.objects.filter(payment_id=data["id"])) == Decimal("1001")
    summary = s.admin.get("/api/v1/contributions/summary/", {"event": str(s.event.pk)}).data
    assert summary["collected"] == "1001.00"
    assert s.admin.get("/api/v1/dues/", {"open": "true"}).data["count"] == 0


def test_visit_cannot_take_more_than_is_owed(setup):
    s = setup
    data = unpaid_pavti(s, received="500")
    too_much = s.admin.post(f"/api/v1/payments/{data['id']}/visit/", {"received": "502"}, format="json")
    assert too_much.status_code == 400
    paid = collect(s.admin, s, [donation(s, "100")]).data
    nothing_owed = s.admin.post(f"/api/v1/payments/{paid['id']}/visit/", {"received": "0"}, format="json")
    assert nothing_owed.status_code == 400


def test_overdue_and_due_today_on_list_and_dashboard(setup):
    s = setup
    overdue = unpaid_pavti(s)
    Payment.objects.filter(pk=overdue["id"]).update(follow_up_on=today(s) - timedelta(days=1))
    due_today = unpaid_pavti(s, follow_up=today(s))
    unpaid_pavti(s, received="200")  # later
    collect(s.admin, s, [donation(s, "100")])  # paid

    listed = s.admin.get("/api/v1/payments/", {"event": str(s.event.pk), "follow_up": "overdue"}).data
    assert [p["id"] for p in listed["results"]] == [overdue["id"]]
    assert listed["results"][0]["follow_up_state"] == "overdue"
    listed = s.admin.get("/api/v1/payments/", {"event": str(s.event.pk), "follow_up": "today"}).data
    assert [p["id"] for p in listed["results"]] == [due_today["id"]]
    assert s.admin.get("/api/v1/payments/", {"event": str(s.event.pk), "pavti": "unpaid"}).data["count"] == 2
    assert s.admin.get("/api/v1/payments/", {"event": str(s.event.pk), "pavti": "partly_paid"}).data["count"] == 1
    assert s.admin.get("/api/v1/payments/", {"event": str(s.event.pk), "pavti": "paid"}).data["count"] == 1

    dashboard = s.admin.get("/api/v1/dashboard/summary/", {"event": str(s.event.pk)}).data
    assert dashboard["follow_ups"]["overdue"] == 1
    assert dashboard["follow_ups"]["due_today"] == 1
    assert dashboard["follow_ups"]["owing"] == 3

    # Paying the overdue pavti takes it off the overdue list.
    s.admin.post(f"/api/v1/payments/{overdue['id']}/visit/", {"received": "1001"}, format="json")
    dashboard = s.admin.get("/api/v1/dashboard/summary/", {"event": str(s.event.pk)}).data
    assert dashboard["follow_ups"]["overdue"] == 0
