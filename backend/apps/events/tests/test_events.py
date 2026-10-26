import pytest
from django.db import IntegrityError, connection, transaction

from apps.contributions.defaults import seed_types
from apps.contributions.models import ContributionType
from apps.events.models import Event, EventParticipant
from apps.organizations.models import FinancialYear
from apps.people.models import Person

pytestmark = pytest.mark.django_db


def fy_of(org):
    return FinancialYear.objects.get(organization=org, is_current=True)


def test_create_event_with_template_and_auto_code(client_for, make_org):
    org = make_org()
    client = client_for(org.admin_user, org)
    response = client.post(
        "/api/v1/events/",
        {"name": "Ganesh Chaturthi 2027", "template": "festival", "financial_year": str(fy_of(org).pk)},
        format="json",
    )
    assert response.status_code == 201, response.data
    assert response.data["code"] == "GC"
    assert response.data["modules"]["collectors"] is True
    second = client.post(
        "/api/v1/events/",
        {"name": "Gauri Celebration", "financial_year": str(fy_of(org).pk), "modules": {"expenses": False}},
        format="json",
    )
    assert second.data["code"] == "GC2"
    assert second.data["modules"]["expenses"] is False
    clash = client.post("/api/v1/events/", {"name": "X", "code": "gc", "financial_year": str(fy_of(org).pk)})
    assert clash.status_code == 400


def test_new_event_gets_default_contribution_types(client_for, make_org):
    org = make_org()
    client = client_for(org.admin_user, org)
    event_id = client.post("/api/v1/events/", {"name": "Navratri 2027", "financial_year": str(fy_of(org).pk)}).data[
        "id"
    ]
    types = client.get("/api/v1/contribution-types/", {"event": event_id}).data["results"]
    assert [(t["name"], t["kind"]) for t in types] == [
        ("Donation", "one_time"),
        ("Membership Fee", "one_time"),
        ("Monthly Contribution", "recurring_monthly"),
        ("Other", "one_time"),
    ]


def test_default_contribution_types_use_org_language_and_skip_existing(make_org):
    org = make_org()
    org.default_language = "mr"
    org.save()
    event = Event.objects.create(organization=org, name="Ganpati", financial_year=fy_of(org), code="G")
    ContributionType.objects.create(organization=org, event=event, name="Monthly", kind="recurring_monthly")
    ContributionType.objects.create(organization=org, event=event, name="Donation")
    seed_types(event)
    seed_types(event)
    names = list(ContributionType.objects.filter(event=event).values_list("name", flat=True))
    assert names == ["Donation", "सभासद शुल्क", "मासिक वर्गणी", "इतर", "Monthly"]


def test_event_templates_listed(client_for, make_user):
    response = client_for(make_user()).get("/api/v1/event-templates/")
    assert {t["code"] for t in response.data} == {"festival", "fundraising", "membership", "society", "custom"}


def test_event_status_transitions(client_for, make_org):
    org = make_org()
    client = client_for(org.admin_user, org)
    event_id = client.post("/api/v1/events/", {"name": "Navratri 2027", "financial_year": str(fy_of(org).pk)}).data[
        "id"
    ]
    assert client.post(f"/api/v1/events/{event_id}/reopen/").status_code == 409
    assert client.post(f"/api/v1/events/{event_id}/close/").data["status"] == "closed"
    assert client.post(f"/api/v1/events/{event_id}/reopen/").data["status"] == "active"


def test_event_cannot_use_another_orgs_financial_year(client_for, make_org):
    a, b = make_org("A"), make_org("B")
    response = client_for(a.admin_user, a).post("/api/v1/events/", {"name": "X", "financial_year": str(fy_of(b).pk)})
    assert response.status_code == 400
    assert "financial_year" in response.data["error"]["details"]


def test_participants_require_event_and_same_org(client_for, make_org):
    a, b = make_org("A"), make_org("B")
    client = client_for(a.admin_user, a)
    event_id = client.post("/api/v1/events/", {"name": "Dahi Handi", "financial_year": str(fy_of(a).pk)}).data["id"]
    mine = Person.objects.create(organization=a, full_name="Mine")
    theirs = Person.objects.create(organization=b, full_name="Theirs")
    assert client.get("/api/v1/event-participants/").status_code == 400
    assert client.post("/api/v1/event-participants/", {"event": event_id, "person": str(theirs.pk)}).status_code == 400
    assert client.post("/api/v1/event-participants/", {"event": event_id, "person": str(mine.pk)}).status_code == 201
    assert client.post("/api/v1/event-participants/", {"event": event_id, "person": str(mine.pk)}).status_code == 400
    assert client.get(f"/api/v1/event-participants/?event={event_id}").data["count"] == 1


def test_database_blocks_cross_org_participant(make_org):
    """Even if application code had a bug, the composite foreign key refuses mixed-organization rows."""
    a, b = make_org("A"), make_org("B")
    event = Event.objects.create(organization=a, financial_year=fy_of(a), name="E", code="E")
    theirs = Person.objects.create(organization=b, full_name="Theirs")
    with pytest.raises(IntegrityError), transaction.atomic():
        EventParticipant.objects.create(organization=a, event=event, person=theirs)
        with connection.cursor() as cursor:
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")


def test_database_blocks_event_with_other_orgs_financial_year(make_org):
    a, b = make_org("A"), make_org("B")
    with pytest.raises(IntegrityError), transaction.atomic():
        Event.objects.create(organization=a, financial_year=fy_of(b), name="E", code="E")
        with connection.cursor() as cursor:
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")


def test_member_sees_only_events_they_take_part_in(client_for, make_org, add_member):
    org = make_org()
    member = add_member(org, "member")
    person = Person.objects.create(organization=org, full_name="Me", user=member)
    joined = Event.objects.create(organization=org, financial_year=fy_of(org), name="Joined", code="J")
    Event.objects.create(organization=org, financial_year=fy_of(org), name="Other", code="O")
    EventParticipant.objects.create(organization=org, event=joined, person=person)
    response = client_for(member, org).get("/api/v1/events/")
    assert [e["name"] for e in response.data["results"]] == ["Joined"]
