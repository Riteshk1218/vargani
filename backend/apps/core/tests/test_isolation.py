"""Data isolation tests (spec §33). Each organization must be invisible to every other organization."""

import uuid
from decimal import Decimal
from types import SimpleNamespace

import pytest

from apps.audit.models import AuditLog
from apps.contributions.models import ContributionType
from apps.events.models import Event, EventParticipant
from apps.funds.models import Fund
from apps.organizations import services as org_services
from apps.organizations.models import FinancialYear, OrganizationMembership
from apps.payments.services import LineInput, record_payment
from apps.people.models import Person

pytestmark = pytest.mark.django_db


@pytest.fixture
def world(make_org, make_user, add_member):
    def build(name):
        org = make_org(name)
        fy = FinancialYear.objects.get(organization=org)
        event = Event.objects.create(organization=org, financial_year=fy, name=f"{name} Festival", code="F")
        person = Person.objects.create(organization=org, full_name=f"{name} Person")
        participant = EventParticipant.objects.create(organization=org, event=event, person=person)
        secretary = add_member(org, "secretary")
        membership = OrganizationMembership.objects.get(organization=org, user=secretary)
        invitation, _ = org_services.create_invitation(
            org=org,
            role=org_services.system_role("member"),
            email=f"invitee-{name}@example.com",
            mobile=None,
            full_name="",
            request=SimpleNamespace(user=org.admin_user, META={}),
        )
        audit_entry = AuditLog.objects.filter(organization=org).first()
        fund = Fund.objects.create(organization=org, event=event, name="General")
        ctype = ContributionType.objects.create(organization=org, event=event, fund=fund, name="Vargani")
        payment, _ = record_payment(
            org=org, event=event, payer=person, mode="cash", lines=[LineInput(ctype, Decimal("100"))]
        )
        return SimpleNamespace(
            fund=fund,
            ctype=ctype,
            payment=payment,
            contribution=payment.lines.get(),
            receipt=payment.receipts.get(),
            org=org,
            fy=fy,
            event=event,
            person=person,
            participant=participant,
            membership=membership,
            invitation=invitation,
            audit=audit_entry,
        )

    return SimpleNamespace(a=build("A"), b=build("B"))


DETAIL_ROUTES = [
    ("people", "person"),
    ("events", "event"),
    ("event-participants", "participant"),
    ("financial-years", "fy"),
    ("members", "membership"),
    ("invitations", "invitation"),
    ("audit-logs", "audit"),
    ("funds", "fund"),
    ("contribution-types", "ctype"),
    ("payments", "payment"),
    ("contributions", "contribution"),
    ("receipts", "receipt"),
]

WRITE_ROUTES = [
    ("patch", "people/{id}/", "person", {"full_name": "Hacked"}),
    ("post", "people/{id}/archive/", "person", {}),
    ("patch", "events/{id}/", "event", {"name": "Hacked"}),
    ("post", "events/{id}/close/", "event", {}),
    ("patch", "event-participants/{id}/", "participant", {"notes": "Hacked"}),
    ("patch", "financial-years/{id}/", "fy", {"label": "Hacked"}),
    ("post", "financial-years/{id}/close/", "fy", {}),
    ("post", "financial-years/{id}/set-current/", "fy", {}),
    ("patch", "members/{id}/", "membership", {"status": "suspended"}),
    ("post", "invitations/{id}/revoke/", "invitation", {}),
    ("patch", "funds/{id}/", "fund", {"name": "Hacked"}),
    ("patch", "contribution-types/{id}/", "ctype", {"name": "Hacked"}),
    ("get", "contribution-types/{id}/outstanding/", "ctype", None),
    ("patch", "payments/{id}/", "payment", {"notes": "Hacked"}),
    ("post", "payments/{id}/confirm/", "payment", {}),
    ("post", "payments/{id}/cancel/", "payment", {}),
]


@pytest.mark.parametrize("route,attr", DETAIL_ROUTES)
def test_1_org_a_cannot_read_org_b_objects(world, client_for, route, attr):
    client = client_for(world.a.org.admin_user, world.a.org)
    target = getattr(world.b, attr)
    assert client.get(f"/api/v1/{route}/{target.pk}/").status_code == 404
    params = f"?event={world.a.event.pk}" if route == "event-participants" else ""
    listing = client.get(f"/api/v1/{route}/{params}").data
    rows = listing["results"] if isinstance(listing, dict) else listing
    assert str(target.pk) not in {str(row["id"]) for row in rows}


@pytest.mark.parametrize("method,path,attr,payload", WRITE_ROUTES)
def test_1_org_a_cannot_change_org_b_objects(world, client_for, method, path, attr, payload):
    client = client_for(world.a.org.admin_user, world.a.org)
    target = getattr(world.b, attr)
    response = getattr(client, method)("/api/v1/" + path.format(id=target.pk), payload, format="json")
    assert response.status_code == 404
    target.refresh_from_db()
    assert getattr(target, "full_name", None) != "Hacked" and getattr(target, "name", None) != "Hacked"


def test_1_org_b_header_is_refused_for_non_member(world, client_for):
    client = client_for(world.a.org.admin_user, world.b.org)
    response = client.get("/api/v1/people/")
    assert response.status_code == 403 and response.data["error"]["code"] == "not_a_member"
    assert client_for(world.a.org.admin_user).get(f"/api/v1/organizations/{world.b.org.pk}/").status_code == 403
    assert client_for(world.a.org.admin_user).get(f"/api/v1/me/organizations/{world.b.org.pk}/").status_code == 403


def test_1_missing_or_unknown_org_header(world, client_for):
    user = world.a.org.admin_user
    response = client_for(user).get("/api/v1/people/")
    assert response.status_code == 400 and response.data["error"]["code"] == "organization_required"
    client = client_for(user)
    client.credentials(HTTP_X_ORGANIZATION_ID=str(uuid.uuid4()))
    assert client.get("/api/v1/people/").status_code == 403
    client.credentials(HTTP_X_ORGANIZATION_ID="not-a-uuid")
    assert client.get("/api/v1/people/").status_code == 403


def test_1_body_cannot_smuggle_another_org(world, client_for):
    client = client_for(world.a.org.admin_user, world.a.org)
    response = client.post("/api/v1/people/", {"full_name": "X", "organization": str(world.b.org.pk)}, format="json")
    assert response.status_code == 201
    assert Person.objects.get(pk=response.data["id"]).organization == world.a.org


def test_1_cross_org_references_in_body_are_rejected(world, client_for):
    client = client_for(world.a.org.admin_user, world.a.org)
    response = client.post(
        "/api/v1/event-participants/", {"event": str(world.b.event.pk), "person": str(world.a.person.pk)}, format="json"
    )
    assert response.status_code == 400
    response = client.post("/api/v1/events/", {"name": "X", "financial_year": str(world.b.fy.pk)}, format="json")
    assert response.status_code == 400
    collect = {
        "event": str(world.a.event.pk),
        "payer": str(world.a.person.pk),
        "mode": "cash",
        "lines": [{"contribution_type": str(world.a.ctype.pk), "amount": "10"}],
    }
    for field, value in [("payer", world.b.person.pk), ("event", world.b.event.pk)]:
        response = client.post("/api/v1/payments/", {**collect, field: str(value)}, format="json")
        assert response.status_code == 400, field
    bad_line = [{"contribution_type": str(world.b.ctype.pk), "amount": "10"}]
    assert client.post("/api/v1/payments/", {**collect, "lines": bad_line}, format="json").status_code == 400
    response = client.post("/api/v1/funds/", {"event": str(world.b.event.pk), "name": "X"}, format="json")
    assert response.status_code == 400
    response = client.post(
        "/api/v1/contribution-types/",
        {"event": str(world.a.event.pk), "fund": str(world.b.fund.pk), "name": "X"},
        format="json",
    )
    assert response.status_code == 400


def test_2_event_a_does_not_show_event_b_data(world, client_for):
    org = world.a.org
    other_event = Event.objects.create(organization=org, financial_year=world.a.fy, name="Navratri", code="N")
    other_person = Person.objects.create(organization=org, full_name="Navratri only")
    EventParticipant.objects.create(organization=org, event=other_event, person=other_person)
    client = client_for(org.admin_user, org)
    rows = client.get(f"/api/v1/event-participants/?event={world.a.event.pk}").data["results"]
    assert {r["person_name"] for r in rows} == {"A Person"}
    rows = client.get(f"/api/v1/event-participants/?event={other_event.pk}").data["results"]
    assert {r["person_name"] for r in rows} == {"Navratri only"}


def test_8_org_switching_changes_data_and_permissions(world, client_for, add_member):
    ritesh = add_member(world.a.org, "org_admin")
    add_member(world.b.org, "volunteer", ritesh)
    in_a = client_for(ritesh, world.a.org)
    in_b = client_for(ritesh, world.b.org)
    assert {p["full_name"] for p in in_a.get("/api/v1/people/").data["results"]} == {"A Person"}
    assert in_a.get("/api/v1/members/").status_code == 200
    # Same user, organization B: volunteer permissions and B data only.
    assert in_b.get("/api/v1/members/").status_code == 403
    assert in_b.get("/api/v1/people/").data["count"] == 0
    assert {e["name"] for e in in_b.get("/api/v1/events/").data["results"]} == {"B Festival"}
    assert in_b.patch(f"/api/v1/organizations/{world.b.org.pk}/", {"name": "x"}).status_code == 403


def test_dashboard_counts_are_per_organization(world, client_for):
    data = client_for(world.a.org.admin_user, world.a.org).get("/api/v1/dashboard/summary/").data
    assert data["people"]["total"] == 1 and data["events"]["total"] == 1
    assert data["financial"]["collected"] == "100.00" and data["financial"]["payments"] == 1
    response = client_for(world.a.org.admin_user, world.a.org).get(
        f"/api/v1/dashboard/summary/?event={world.b.event.pk}"
    )
    assert response.status_code == 404
