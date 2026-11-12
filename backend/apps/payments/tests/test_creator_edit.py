"""The person who created a pavti edits it in place (same number), and the receipts list shows and filters
by who created each pavti."""

import pytest

from apps.audit.models import AuditLog
from apps.receipts.models import Receipt

from .test_admin_edit import donation, post
from .test_payments import setup  # noqa: F401 - fixture

pytestmark = pytest.mark.django_db


def test_creator_edits_own_pavti_amount_and_keeps_the_number(setup, add_member, client_for):  # noqa: F811
    s = setup
    user = add_member(s.org, "collector")
    collector = client_for(user, s.org)
    created = post(collector, s, [donation(s, "500")])
    assert created.status_code == 201, created.data
    payment_id = created.data["id"]
    assert created.data["can_edit"] is True
    number = Receipt.objects.get().receipt_number
    receipt = collector.get(f"/api/v1/receipts/{created.data['receipt']['id']}/").data
    assert receipt["can_edit"] is True and receipt["created_by"] == str(user.pk)

    edited = collector.post(
        f"/api/v1/payments/{payment_id}/edit/",
        {"lines": [donation(s, "750")], "mode": "upi", "reference_number": "UPI9"},
        format="json",
    )
    assert edited.status_code == 200, edited.data
    assert edited.data["amount"] == "750.00" and edited.data["mode"] == "upi"
    receipt = Receipt.objects.get()  # still one pavti
    assert receipt.receipt_number == number and receipt.status == "issued"
    assert receipt.snapshot["total"] == "750.00"
    log = AuditLog.objects.get(entity_id=payment_id, action="pavti_edit")
    assert log.before["amount"] == "500.00" and log.after["amount"] == "750.00"
    assert log.actor_user_id == user.pk


def test_others_cannot_edit_a_pavti_they_did_not_create(setup, add_member, client_for):  # noqa: F811
    s = setup
    owner = client_for(add_member(s.org, "collector"), s.org)
    payment_id = post(owner, s, [donation(s, "500")]).data["id"]
    other = client_for(add_member(s.org, "collector"), s.org)
    response = other.post(f"/api/v1/payments/{payment_id}/edit/", {"notes": "x"}, format="json")
    assert response.status_code in (403, 404)

    # A treasurer sees the pavti but did not create it, so cannot edit it.
    treasurer = client_for(add_member(s.org, "treasurer"), s.org)
    response = treasurer.get(f"/api/v1/payments/{payment_id}/")
    assert response.status_code == 200 and response.data["can_edit"] is False
    assert treasurer.post(f"/api/v1/payments/{payment_id}/edit/", {"notes": "x"}, format="json").status_code == 403

    # The admin keeps editing every pavti.
    assert s.admin.get(f"/api/v1/payments/{payment_id}/").data["can_edit"] is True
    edited = s.admin.post(f"/api/v1/payments/{payment_id}/edit/", {"lines": [donation(s, "100")]}, format="json")
    assert edited.status_code == 200 and edited.data["amount"] == "100.00"
    assert AuditLog.objects.filter(entity_id=payment_id, action="admin_edit").exists()


def test_creator_cannot_move_pavti_to_someone_not_assigned(setup, add_member, client_for):  # noqa: F811
    s = setup
    collector = client_for(add_member(s.org, "collector"), s.org)
    payment_id = post(collector, s, [donation(s)]).data["id"]
    response = collector.post(f"/api/v1/payments/{payment_id}/edit/", {"payer": str(s.ritesh.pk)}, format="json")
    assert response.status_code == 403


def test_receipts_list_filters_by_creator(setup, add_member, client_for):  # noqa: F811
    s = setup
    kiran = add_member(s.org, "collector")
    post(client_for(kiran, s.org), s, [donation(s, "200")])
    post(s.admin, s, [donation(s, "300")])
    listed = s.admin.get("/api/v1/receipts/").data["results"]
    assert {r["created_by_name"] for r in listed} == {kiran.full_name, s.org.admin_user.full_name}

    mine = s.admin.get("/api/v1/receipts/", {"created_by": str(kiran.pk)}).data["results"]
    assert [r["amount"] for r in mine] == ["200.00"]

    creators = s.admin.get("/api/v1/receipts/creators/").data
    assert {c["id"] for c in creators} == {str(kiran.pk), str(s.org.admin_user.pk)}
