import pytest

from apps.audit.models import AuditLog
from apps.people.models import Person

pytestmark = pytest.mark.django_db


def test_create_search_filter_archive(client_for, make_org):
    org = make_org()
    client = client_for(org.admin_user, org)
    response = client.post(
        "/api/v1/people/",
        {
            "full_name": "  Ritesh   Patil ",
            "mobile": "98123 45678",
            "person_types": ["karyakarta", "member", "member"],
            "area": "Sadashiv Peth",
        },
        format="json",
    )
    assert response.status_code == 201, response.data
    assert response.data["full_name"] == "Ritesh Patil"
    assert response.data["mobile"] == "+919812345678"
    assert response.data["person_types"] == ["karyakarta", "member"]
    client.post("/api/v1/people/", {"full_name": "Sunita Joshi", "person_types": ["donor"]}, format="json")

    assert client.get("/api/v1/people/?search=ritesh").data["count"] == 1
    assert client.get("/api/v1/people/?search=98123").data["count"] == 1
    assert client.get("/api/v1/people/?person_type=donor").data["count"] == 1

    person_id = response.data["id"]
    assert client.post(f"/api/v1/people/{person_id}/archive/").status_code == 200
    assert client.get("/api/v1/people/").data["count"] == 1
    assert client.get(f"/api/v1/people/{person_id}/").status_code == 404
    assert Person.objects.filter(pk=person_id).exists()  # soft deleted, not removed
    assert AuditLog.objects.filter(entity_id=person_id, action="soft_delete").exists()


def test_people_cannot_be_hard_deleted(client_for, make_org):
    org = make_org()
    client = client_for(org.admin_user, org)
    person_id = client.post("/api/v1/people/", {"full_name": "A"}, format="json").data["id"]
    assert client.delete(f"/api/v1/people/{person_id}/").status_code == 405


def test_duplicate_mobile_is_a_warning_not_an_error(client_for, make_org):
    org = make_org()
    client = client_for(org.admin_user, org)
    client.post("/api/v1/people/", {"full_name": "Father", "mobile": "9812345678"}, format="json")
    response = client.post("/api/v1/people/", {"full_name": "Son", "mobile": "9812345678"}, format="json")
    assert response.status_code == 201
    matches = client.get("/api/v1/people/check-duplicates/?mobile=+919812345678").data["results"]
    assert len(matches) == 2


def test_invalid_mobile_rejected(client_for, make_org):
    org = make_org()
    response = client_for(org.admin_user, org).post("/api/v1/people/", {"full_name": "A", "mobile": "12ab"})
    assert response.status_code == 400
    assert "mobile" in response.data["error"]["details"]


def test_member_sees_only_own_person(client_for, make_org, add_member):
    org = make_org()
    member_user = add_member(org, "member")
    Person.objects.create(organization=org, full_name="Other")
    response = client_for(member_user, org).get("/api/v1/people/")
    assert response.status_code == 403  # members have no people.view; they use the member portal


def test_collector_sees_no_unassigned_people_and_cannot_quick_add_by_default(client_for, make_org, add_member):
    org = make_org()
    collector = add_member(org, "collector")
    Person.objects.create(organization=org, full_name="Someone")
    client = client_for(collector, org)
    assert client.get("/api/v1/people/").data["count"] == 0
    assert client.post("/api/v1/people/", {"full_name": "Walk-in"}).status_code == 403
    org.settings["allow_unassigned_collection"] = True
    org.save()
    assert client.post("/api/v1/people/", {"full_name": "Walk-in"}).status_code == 201
