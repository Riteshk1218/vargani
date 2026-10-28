"""Organization Admin (and platform admin) delete many rows of a list at once with POST <list>/bulk-delete/."""

import pytest

from apps.audit.models import AuditLog
from apps.contributions.models import Contribution
from apps.payments.models import Payment
from apps.payments.tests.test_admin_edit import donation, post
from apps.payments.tests.test_payments import setup  # noqa: F401 - fixture
from apps.people.models import Person
from apps.receipts.models import Receipt

pytestmark = pytest.mark.django_db


def bulk(client, path, ids):
    return client.post(f"/api/v1/{path}/bulk-delete/", {"ids": [str(i) for i in ids]}, format="json")


def test_admin_deletes_many_collections_at_once(setup):  # noqa: F811
    s = setup
    ids = [post(s.admin, s, [donation(s, str(100 + n))]).data["id"] for n in range(3)]
    response = bulk(s.admin, "payments", ids[:2])
    assert response.status_code == 200, response.data
    assert response.data == {"deleted": 2, "failed": []}
    assert [p["id"] for p in s.admin.get("/api/v1/payments/").data["results"]] == [ids[2]]
    assert Receipt.objects.filter(payment_id__in=ids[:2], status="void").count() == 2
    assert AuditLog.objects.filter(entity_id__in=ids[:2], action="admin_delete").count() == 2
    # Deleting again is reported, not an error for the whole request.
    again = bulk(s.admin, "payments", ids[:1]).data
    assert again["deleted"] == 0 and len(again["failed"]) == 1


def test_deleting_contribution_lines_or_receipts_deletes_their_collection(setup):  # noqa: F811
    s = setup
    two_lines = post(s.admin, s, [donation(s, "100"), donation(s, "200")]).data["id"]
    other = post(s.admin, s, [donation(s, "300")]).data["id"]
    lines = Contribution.objects.filter(payment_id=two_lines).values_list("pk", flat=True)
    assert bulk(s.admin, "contributions", lines).data == {"deleted": 1, "failed": []}
    assert Payment.objects.get(pk=two_lines).status == "deleted"
    listed = s.admin.get("/api/v1/contributions/", {"event": str(s.event.pk)}).data["results"]
    assert {str(c["payment"]) for c in listed} == {other}

    receipt = Receipt.objects.get(payment_id=other)
    assert bulk(s.admin, "receipts", [receipt.pk]).data == {"deleted": 1, "failed": []}
    assert Payment.objects.get(pk=other).status == "deleted"
    assert s.admin.get("/api/v1/receipts/").data["count"] == 0


def test_bulk_delete_people_and_events(setup):  # noqa: F811
    s = setup
    extra = Person.objects.create(organization=s.org, full_name="Someone Else")
    assert bulk(s.admin, "people", [s.ritesh.pk, extra.pk]).data["deleted"] == 2
    assert s.admin.get("/api/v1/people/").data["count"] == 0
    assert bulk(s.admin, "events", [s.event.pk]).data["deleted"] == 1
    assert s.admin.get("/api/v1/events/").data["count"] == 0


def test_admin_cannot_bulk_delete_own_access(setup, add_member):  # noqa: F811
    s = setup
    collector = add_member(s.org, "collector")
    members = {m["user"]["id"]: m["id"] for m in s.admin.get("/api/v1/members/").data["results"]}
    result = bulk(s.admin, "members", [members[str(collector.pk)], members[str(s.org.admin_user.pk)]]).data
    assert result["deleted"] == 1 and len(result["failed"]) == 1


def test_only_the_admin_or_platform_admin_bulk_deletes(setup, add_member, client_for):  # noqa: F811
    s = setup
    payment_id = post(s.admin, s, [donation(s)]).data["id"]
    treasurer_user = add_member(s.org, "treasurer")
    treasurer = client_for(treasurer_user, s.org)
    assert bulk(treasurer, "payments", [payment_id]).status_code == 403
    treasurer_user.is_platform_admin = True
    treasurer_user.save(update_fields=["is_platform_admin"])
    detail = client_for(treasurer_user).get(f"/api/v1/me/organizations/{s.org.pk}/").data
    assert "records.admin_edit" in detail["permissions"]
    assert bulk(client_for(treasurer_user, s.org), "payments", [payment_id]).data["deleted"] == 1
