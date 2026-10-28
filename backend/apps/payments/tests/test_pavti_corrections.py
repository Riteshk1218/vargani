"""Correcting a pavti's amount (also when it keeps a balance), the signatory name and the receipt language."""

import pytest
from rest_framework.test import APIClient

from apps.contributions.models import Due
from apps.receipts.models import Receipt
from apps.receipts.rendering import create_share, receipt_pdf

from .test_payments import setup  # noqa: F401 - fixture

pytestmark = pytest.mark.django_db


def donation(s, amount):
    return {"contribution_type": str(s.donation.pk), "amount": amount}


def collect(s, amount, **extra):
    payload = {"event": str(s.event.pk), "mode": "cash", "payer": str(s.ritesh.pk), "lines": [donation(s, amount)]}
    response = s.admin.post("/api/v1/collections/", {**payload, **extra}, format="json")
    assert response.status_code == 201, response.data
    return response.data


def correct(s, data, amount):
    line = data["lines"][0]["id"]
    return s.admin.post(f"/api/v1/payments/{data['id']}/edit/", {"line_amounts": {line: amount}}, format="json")


def test_wrong_amount_is_corrected_and_the_pavti_keeps_its_number(setup):  # noqa: F811
    s = setup
    data = collect(s, "500")
    assert data["keeps_balance"] is False
    number = Receipt.objects.get().receipt_number
    found = s.admin.get("/api/v1/receipts/", {"search": number}).data["results"]
    assert [r["receipt_number"] for r in found] == [number]

    edited = correct(s, data, "400")
    assert edited.status_code == 200, edited.data
    assert edited.data["amount"] == "400.00" and edited.data["lines"][0]["amount"] == "400.00"
    receipt = Receipt.objects.get()
    assert receipt.receipt_number == number and receipt.snapshot["total"] == "400.00"
    assert s.admin.get("/api/v1/finance/summary/").data["total"]["collection"] == "400.00"


def test_correction_on_a_pavti_with_a_balance_moves_the_balance(setup):  # noqa: F811
    s = setup
    data = collect(s, "1000", received="500")
    assert data["keeps_balance"] is True and data["balance_due"] == "500.00"
    # Changing the lines is refused on a pavti with a balance; correcting the amount is allowed.
    refused = s.admin.post(f"/api/v1/payments/{data['id']}/edit/", {"lines": [donation(s, "400")]}, format="json")
    assert refused.status_code == 400

    edited = correct(s, data, "400")
    assert edited.status_code == 200, edited.data
    assert edited.data["amount"] == "400.00" and edited.data["balance_due"] == "600.00"
    assert Due.objects.get().amount == 600
    snapshot = Receipt.objects.get().snapshot
    assert snapshot["total"] == "400.00" and snapshot["balance_total"] == "600.00"

    # Received the full amount after all: the balance closes.
    full = correct(s, data, "1000")
    assert full.status_code == 200, full.data
    assert full.data["balance_due"] == "0.00" and full.data["pavti_status"] == "paid"
    assert Due.objects.get().status == Due.Status.CANCELLED


def test_correction_of_a_later_visit_stays_within_the_balance(setup):  # noqa: F811
    s = setup
    data = collect(s, "1000", received="400")
    visit = s.admin.post(f"/api/v1/payments/{data['id']}/visit/", {"received": "300"}, format="json").data
    later = next(line for line in visit["lines"] if line["towards_balance"])
    path = f"/api/v1/payments/{data['id']}/edit/"
    assert s.admin.post(path, {"line_amounts": {later["id"]: "601"}}, format="json").status_code == 400
    edited = s.admin.post(path, {"line_amounts": {later["id"]: "250"}}, format="json")
    assert edited.status_code == 200, edited.data
    assert edited.data["amount"] == "650.00" and edited.data["balance_due"] == "350.00"
    # The first line can no longer take more than what is still owed plus what the visit settled.
    first = next(line for line in visit["lines"] if not line["towards_balance"])
    assert s.admin.post(path, {"line_amounts": {first["id"]: "800"}}, format="json").status_code == 400
    unknown = s.admin.post(path, {"line_amounts": {str(s.event.pk): "10"}}, format="json")
    assert unknown.status_code == 400


def test_receipt_names_the_signatory_and_prints_in_any_language(setup):  # noqa: F811
    s = setup
    collect(s, "500")
    receipt = Receipt.objects.get()
    assert receipt.snapshot["signatory"] == s.org.admin_user.full_name
    assert receipt_pdf(receipt, "mr")[:4] == b"%PDF"
    response = s.admin.get(f"/api/v1/receipts/{receipt.pk}/pdf/", {"language": "mr"})
    assert response.status_code == 200 and response["Content-Type"] == "application/pdf"
    assert "नमस्कार" in create_share(receipt, language="mr")["whatsapp_text"]
    shared = s.admin.post(f"/api/v1/receipts/{receipt.pk}/share/", {"language": "hi"}, format="json")
    assert shared.status_code == 200
    token = shared.data["share_url"].rsplit("/", 1)[-1]
    public = APIClient().get(f"/api/v1/public/receipts/{token}/").data
    assert public["snapshot"]["signatory"] == s.org.admin_user.full_name
    assert "collector" not in public["snapshot"]


def test_people_download_has_contact_details(setup):  # noqa: F811
    s = setup
    response = s.admin.get("/api/v1/people/download/", {"file": "csv", "person_type": ""})
    assert response.status_code == 200
    text = response.content.decode("utf-8-sig")
    assert "Mobile" in text and "Email" in text and "Alternate mobile" in text
    assert "+919812345678" in text
