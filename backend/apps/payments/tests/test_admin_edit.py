"""Optional contributor (existing, new or anonymous), admin edit and delete, and the financial summary."""

from datetime import date
from decimal import Decimal

import pytest

from apps.audit.models import AuditLog
from apps.contributions.models import CollectorAssignment, Contribution
from apps.expenses.models import Expense, ExpenseCategory
from apps.payments.models import Payment
from apps.people.models import Person
from apps.receipts.models import Receipt
from apps.receipts.rendering import create_share, receipt_pdf

from .test_payments import month_line, setup  # noqa: F401 - fixture

pytestmark = pytest.mark.django_db


def donation(s, amount="500"):
    return {"contribution_type": str(s.donation.pk), "amount": amount}


def post(client, s, lines, **extra):
    payload = {"event": str(s.event.pk), "mode": "cash", "lines": lines, **extra}
    return client.post("/api/v1/collections/", payload, format="json")


def test_anonymous_collection_gets_a_receipt(setup):  # noqa: F811
    s = setup
    response = post(s.admin, s, [donation(s, "101")])
    assert response.status_code == 201, response.data
    data = response.data
    assert data["payer"] is None and data["is_anonymous"] is True and data["payer_name"] == "Anonymous"
    assert data["event_name"] == "Ganesh Chaturthi 2027" and data["financial_year_label"]
    assert data["paid_at"] and data["receipt"]["receipt_number"] == "GC-2027-00001"
    receipt = Receipt.objects.get()
    assert receipt.snapshot["person"]["anonymous"] is True
    assert receipt.snapshot["timezone"] == "Asia/Kolkata"
    assert receipt_pdf(receipt)[:4] == b"%PDF"
    assert "Namaskar Anonymous" in create_share(receipt)["whatsapp_text"]
    listed = s.admin.get("/api/v1/receipts/").data["results"][0]
    assert listed["payer_name"] == "Anonymous"
    assert s.admin.get("/api/v1/reports/receipts/").status_code == 200
    assert s.admin.get("/api/v1/reports/contributions/").status_code == 200


def test_new_person_is_created_with_the_collection(setup):  # noqa: F811
    s = setup
    response = post(s.admin, s, [donation(s)], new_person={"full_name": "  Sunita  More ", "mobile": "9822012345"})
    assert response.status_code == 201, response.data
    person = Person.objects.get(full_name="Sunita More")
    assert person.mobile == "+919822012345"
    assert response.data["payer"] == person.pk and response.data["payer_name"] == "Sunita More"
    both = post(s.admin, s, [donation(s)], payer=str(s.ritesh.pk), new_person={"full_name": "X"})
    assert both.status_code == 400
    assert post(s.admin, s, [donation(s)], new_person={"full_name": " "}).status_code == 400


def test_collector_can_collect_anonymously_and_add_people(setup, add_member, client_for):  # noqa: F811
    s = setup
    user = add_member(s.org, "collector")
    collector = client_for(user, s.org)
    # Not assigned to Ritesh: refused as before.
    assert post(collector, s, [donation(s)], payer=str(s.ritesh.pk)).status_code == 403
    assert post(collector, s, [donation(s)]).status_code == 201
    created = post(collector, s, [donation(s)], new_person={"full_name": "Asha Jadhav"})
    assert created.status_code == 201, created.data
    # The new person is assigned to the collector, so they find them next time.
    person = Person.objects.get(full_name="Asha Jadhav")
    assert CollectorAssignment.objects.filter(person=person, event=s.event, collector__user=user).exists()
    names = [p["full_name"] for p in collector.get("/api/v1/people/").data["results"]]
    assert names == ["Asha Jadhav"]
    assert post(collector, s, [donation(s)], payer=str(person.pk)).status_code == 201


def test_admin_edits_a_collection_and_keeps_the_receipt_number(setup):  # noqa: F811
    s = setup
    payment_id = post(s.admin, s, [donation(s, "500")], payer=str(s.ritesh.pk)).data["id"]
    number = Receipt.objects.get().receipt_number
    edited = s.admin.post(
        f"/api/v1/payments/{payment_id}/edit/",
        {
            "payer": None,
            "mode": "upi",
            "reference_number": "UPI123",
            "lines": [donation(s, "300"), month_line(s, "2027-05-01", "200.50")],
            "notes": "Corrected",
        },
        format="json",
    )
    assert edited.status_code == 200, edited.data
    assert edited.data["amount"] == "500.50" and edited.data["is_anonymous"] and edited.data["mode"] == "upi"
    assert len(edited.data["lines"]) == 2
    receipt = Receipt.objects.get()
    assert receipt.receipt_number == number and receipt.status == "issued"
    assert receipt.snapshot["total"] == "500.50" and receipt.snapshot["person"]["anonymous"]
    assert Contribution.objects.filter(payment_id=payment_id).count() == 2
    log = AuditLog.objects.get(entity_id=payment_id, action="admin_edit")
    assert log.before["amount"] == "500.00" and log.after["amount"] == "500.50"

    # Back to a named person, created on the spot.
    renamed = s.admin.post(
        f"/api/v1/payments/{payment_id}/edit/", {"new_person": {"full_name": "Meera Kale"}}, format="json"
    )
    assert renamed.data["payer_name"] == "Meera Kale"
    assert Contribution.objects.filter(payment_id=payment_id, person__full_name="Meera Kale").count() == 2


def test_only_the_admin_edits_or_deletes(setup, add_member, client_for):  # noqa: F811
    s = setup
    payment_id = post(s.admin, s, [donation(s)], payer=str(s.ritesh.pk)).data["id"]
    treasurer = client_for(add_member(s.org, "treasurer"), s.org)
    assert treasurer.post(f"/api/v1/payments/{payment_id}/edit/", {"notes": "x"}, format="json").status_code == 403
    assert treasurer.delete(f"/api/v1/payments/{payment_id}/").status_code == 403


def test_admin_deletes_a_collection(setup):  # noqa: F811
    s = setup
    keep = post(s.admin, s, [donation(s, "700")], payer=str(s.ritesh.pk)).data["id"]
    gone = post(s.admin, s, [donation(s, "300")]).data["id"]
    deleted = s.admin.delete(f"/api/v1/payments/{gone}/", {"reason": "Entered twice"}, format="json")
    assert deleted.status_code == 200 and deleted.data["status"] == "deleted"
    assert Payment.objects.filter(pk=gone).exists()  # kept for the audit trail
    receipt = Receipt.objects.get(payment_id=gone)
    assert receipt.status == "void" and receipt.void_reason == "Entered twice"
    assert [p["id"] for p in s.admin.get("/api/v1/payments/").data["results"]] == [keep]
    summary = s.admin.get("/api/v1/finance/summary/").data
    assert summary["total"]["collection"] == "700.00"
    assert s.admin.delete(f"/api/v1/payments/{gone}/").status_code == 409
    assert AuditLog.objects.filter(entity_id=gone, action="admin_delete").exists()


def test_financial_summary_per_event(setup):  # noqa: F811
    s = setup
    from apps.events.models import Event

    other = Event.objects.create(
        organization=s.org, financial_year=s.fy, name="Navratri 2027", code="NV", start_date=date(2027, 10, 1)
    )
    post(s.admin, s, [donation(s, "150000")])
    category = ExpenseCategory.objects.filter(organization=s.org).first()
    for amount, status in (("35000", "approved"), ("5000", "submitted"), ("1000", "rejected"), ("700", "draft")):
        Expense.objects.create(
            organization=s.org,
            financial_year=s.fy,
            event=s.event,
            category=category,
            amount=Decimal(amount),
            expense_date=date.today(),
            status=status,
        )
    data = s.admin.get("/api/v1/finance/summary/", {"financial_year": str(s.fy.pk)}).data
    rows = {row["event"]["name"]: row for row in data["events"]}
    gc = rows["Ganesh Chaturthi 2027"]
    assert gc["collection"] == "150000.00" and gc["approved_expenses"] == "35000.00"
    assert gc["balance"] == "115000.00"
    assert gc["pending_expenses"] == "5000.00" and gc["rejected_expenses"] == "1000.00"
    assert gc["financial_year"]["label"] == s.fy.label
    assert rows[other.name]["collection"] == "0.00" and rows[other.name]["balance"] == "0.00"
    assert data["total"]["balance"] == "115000.00"
    only = s.admin.get("/api/v1/finance/summary/", {"event": str(other.pk)}).data
    assert [r["event"]["name"] for r in only["events"]] == ["Navratri 2027"]
