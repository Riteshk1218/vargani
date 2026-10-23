# ruff: noqa: F811
"""Balances (baaki): the receipt is given before all of the money comes."""

from decimal import Decimal

import pytest

from apps.contributions.models import Contribution, Due
from apps.payments.models import Payment
from apps.receipts.models import Receipt

from .test_payments import collect, setup  # noqa: F401

pytestmark = pytest.mark.django_db


def donation(s, amount):
    return {"contribution_type": str(s.donation.pk), "amount": amount}


def test_part_received_keeps_the_rest_as_balance(setup):
    s = setup
    response = collect(s.admin, s, [donation(s, "1000")], received="400")
    assert response.status_code == 201, response.data
    payment = Payment.objects.get(pk=response.data["id"])
    assert payment.amount == Decimal("400")
    assert [c.amount for c in payment.lines.all()] == [Decimal("400")]
    due = Due.objects.get(payment=payment)
    assert due.amount == Decimal("600") and due.person == s.ritesh
    snapshot = Receipt.objects.get(payment=payment).snapshot
    assert snapshot["total"] == "400.00" and snapshot["balance_total"] == "600.00"
    summary = s.admin.get("/api/v1/contributions/summary/", {"event": str(s.event.pk)}).data
    assert summary["collected"] == "400.00"  # a balance is not money collected


def test_nothing_received_still_gives_a_receipt(setup):
    s = setup
    response = collect(s.admin, s, [donation(s, "700")], received="0")
    assert response.status_code == 201, response.data
    payment = Payment.objects.get(pk=response.data["id"])
    assert payment.amount == 0 and not payment.lines.exists()
    assert Receipt.objects.filter(payment=payment, status="issued").exists()
    dues = s.admin.get("/api/v1/dues/", {"person": str(s.ritesh.pk), "open": "true"}).data["results"]
    assert [(d["amount"], d["remaining"]) for d in dues] == [("700.00", "700.00")]
    assert dues[0]["receipt_number"] == Receipt.objects.get(payment=payment).receipt_number


def test_paying_the_balance_later(setup):
    s = setup
    collect(s.admin, s, [donation(s, "1000")], received="400")
    due = Due.objects.get()
    over = collect(s.admin, s, [{"due": str(due.pk), "amount": "700"}])
    assert over.status_code == 400
    part = collect(s.admin, s, [{"due": str(due.pk), "amount": "200"}])
    assert part.status_code == 201, part.data
    line = Contribution.objects.get(payment_id=part.data["id"])
    assert line.due == due and line.contribution_type == s.donation
    snapshot = Receipt.objects.get(payment_id=part.data["id"]).snapshot
    assert snapshot["lines"][0]["towards_balance"] is True and snapshot["balance_total"] == "400.00"
    rest = collect(s.admin, s, [{"due": str(due.pk), "amount": "400"}])
    assert rest.status_code == 201
    assert s.admin.get("/api/v1/dues/", {"open": "true"}).data["count"] == 0
    report = s.admin.get("/api/v1/reports/balances/", {"event": str(s.event.pk)}).data
    assert report["rows"] == []


def test_balance_needs_a_named_person_and_a_valid_amount(setup):
    s = setup
    payload = {"event": str(s.event.pk), "mode": "cash", "lines": [donation(s, "500")], "received": "100"}
    assert s.admin.post("/api/v1/payments/", payload, format="json").status_code == 400
    assert collect(s.admin, s, [donation(s, "500")], received="600").status_code == 400


def test_balance_report_and_write_off(setup):
    s = setup
    collect(s.admin, s, [donation(s, "1000")], received="250")
    report = s.admin.get("/api/v1/reports/balances/", {"event": str(s.event.pk)}).data
    assert report["totals"]["remaining"] == "750.00"
    assert report["rows"][0]["person"] == "Ritesh Patil"
    due = Due.objects.get()
    assert s.admin.post(f"/api/v1/dues/{due.pk}/cancel/", {"reason": "Moved away"}).status_code == 200
    assert s.admin.get("/api/v1/reports/balances/", {"event": str(s.event.pk)}).data["rows"] == []


def test_deleting_the_collection_cancels_its_balance(setup):
    s = setup
    response = collect(s.admin, s, [donation(s, "1000")], received="400")
    deleted = s.admin.delete(f"/api/v1/payments/{response.data['id']}/", {"reason": "Wrong person"}, format="json")
    assert deleted.status_code == 200, deleted.data
    assert Due.objects.get().status == Due.Status.CANCELLED


def test_receipt_pdf_and_whatsapp_show_the_balance(setup):
    s = setup
    response = collect(s.admin, s, [donation(s, "1000")], received="0")
    receipt_id = response.data["receipt"]["id"]
    pdf = s.admin.get(f"/api/v1/receipts/{receipt_id}/pdf/")
    assert pdf.status_code == 200 and pdf["Content-Type"] == "application/pdf"
    share = s.admin.post(f"/api/v1/receipts/{receipt_id}/share/")
    assert "Balance due: Rs 1,000.00" in share.data["whatsapp_text"]
