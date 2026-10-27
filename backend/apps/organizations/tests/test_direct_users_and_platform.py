import pytest

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.organizations.models import Invitation, Organization, OrganizationMembership
from conftest import DEFAULT_PASSWORD

pytestmark = pytest.mark.django_db

NEW_PASSWORD = "Ganpati-Bappa-2027"


def _role_id(client, code):
    return next(r["id"] for r in client.get("/api/v1/roles/").data if r["code"] == code)


def org_client(client_for, org, user):
    return client_for(user, org)


# --- Admin adds a user with a password -----------------------------------------
def test_admin_adds_user_with_password_who_can_log_in(client_for, make_org, api):
    org = make_org()
    client = org_client(client_for, org, org.admin_user)
    response = client.post(
        "/api/v1/members/",
        {
            "full_name": "Sagar Patil",
            "mobile": "9876543210",
            "password": NEW_PASSWORD,
            "role_id": _role_id(client, "collector"),
        },
        format="json",
    )
    assert response.status_code == 201, response.data
    assert response.data["new_login"] is True
    assert response.data["role"]["code"] == "collector"
    assert response.data["can_reset_password"] is True
    login = api.post("/api/v1/auth/login/", {"identifier": "9876543210", "password": NEW_PASSWORD}, format="json")
    assert login.status_code == 200, login.data
    assert AuditLog.objects.filter(organization=org, action="role_change", after__reason="added_by_admin").exists()


def test_adding_existing_login_keeps_their_password(client_for, make_org, make_user, api):
    org = make_org()
    other = make_org("Other")
    person = make_user(email="sagar@example.com")
    OrganizationMembership.objects.create(organization=other, user=person, role=other.memberships.first().role)
    client = org_client(client_for, org, org.admin_user)
    response = client.post(
        "/api/v1/members/",
        {
            "full_name": "Sagar",
            "email": "SAGAR@example.com",
            "password": NEW_PASSWORD,
            "role_id": _role_id(client, "treasurer"),
        },
        format="json",
    )
    assert response.status_code == 201, response.data
    assert response.data["new_login"] is False
    assert response.data["can_reset_password"] is False
    person.refresh_from_db()
    assert not person.check_password(NEW_PASSWORD)


def test_adding_revokes_pending_invitation(client_for, make_org):
    org = make_org()
    client = org_client(client_for, org, org.admin_user)
    role_id = _role_id(client, "collector")
    client.post("/api/v1/invitations/", {"mobile": "9876543210", "role_id": role_id}, format="json")
    client.post(
        "/api/v1/members/",
        {"full_name": "Sagar", "mobile": "9876543210", "password": NEW_PASSWORD, "role_id": role_id},
        format="json",
    )
    assert Invitation.objects.get(organization=org).status == Invitation.Status.REVOKED


def test_add_user_rejects_weak_password_and_existing_member(client_for, make_org):
    org = make_org()
    client = org_client(client_for, org, org.admin_user)
    role_id = _role_id(client, "collector")
    weak = client.post(
        "/api/v1/members/", {"full_name": "A", "mobile": "9876543210", "password": "123", "role_id": role_id}
    )
    assert weak.status_code == 400
    again = client.post(
        "/api/v1/members/",
        {"full_name": "A", "email": org.admin_user.email, "password": NEW_PASSWORD, "role_id": role_id},
    )
    assert again.status_code == 400


def test_only_member_managers_can_add_users(client_for, make_org, add_member):
    org = make_org()
    treasurer = add_member(org, "treasurer")
    role_id = _role_id(org_client(client_for, org, org.admin_user), "collector")
    response = org_client(client_for, org, treasurer).post(
        "/api/v1/members/", {"full_name": "A", "mobile": "9876543210", "password": NEW_PASSWORD, "role_id": role_id}
    )
    assert response.status_code == 403


def test_admin_sets_password_only_for_own_org_logins(client_for, make_org, add_member, api):
    org, other = make_org(), make_org("Other")
    collector = add_member(org, "collector")
    shared = add_member(org, "collector")
    add_member(other, "collector", shared)
    client = org_client(client_for, org, org.admin_user)
    membership = OrganizationMembership.objects.get(organization=org, user=collector)
    response = client.post(f"/api/v1/members/{membership.pk}/set-password/", {"password": NEW_PASSWORD})
    assert response.status_code == 200, response.data
    login = api.post("/api/v1/auth/login/", {"identifier": collector.email, "password": NEW_PASSWORD}, format="json")
    assert login.status_code == 200

    shared_membership = OrganizationMembership.objects.get(organization=org, user=shared)
    refused = client.post(f"/api/v1/members/{shared_membership.pk}/set-password/", {"password": NEW_PASSWORD})
    assert refused.status_code == 422
    # A membership of another organization is not reachable at all.
    foreign = OrganizationMembership.objects.get(organization=other, user=other.admin_user)
    assert client.post(f"/api/v1/members/{foreign.pk}/set-password/", {"password": NEW_PASSWORD}).status_code == 404


# --- Platform owner ---------------------------------------------------------------
@pytest.fixture
def owner(make_user):
    return make_user(full_name="Owner", is_platform_admin=True)


def test_platform_pages_are_for_the_platform_admin_only(client_for, make_org):
    org = make_org()
    client = client_for(org.admin_user)
    for path in ("summary", "organizations", "users"):
        assert client.get(f"/api/v1/platform/{path}/").status_code == 403


def test_owner_sees_every_organization_with_admins_and_counts(client_for, make_org, add_member, owner):
    a, b = make_org("Ganesh Mandal"), make_org("Navratri Mandal")
    add_member(a, "collector")
    client = client_for(owner)
    response = client.get("/api/v1/platform/organizations/")
    assert response.status_code == 200
    rows = {row["name"]: row for row in response.data["results"]}
    assert set(rows) == {"Ganesh Mandal", "Navratri Mandal"}
    assert rows["Ganesh Mandal"]["users_count"] == 2
    assert rows["Ganesh Mandal"]["admins"][0]["email"] == a.admin_user.email
    assert "total" not in str(rows["Ganesh Mandal"]).lower()  # no money figures
    users = client.get("/api/v1/platform/users/", {"search": "Navratri"}).data["results"]
    assert [u["full_name"] for u in users] == [b.admin_user.full_name]
    summary = client.get("/api/v1/platform/summary/").data
    assert summary["organizations"]["total"] == 2


def test_owner_creates_organization_with_admin_login(client_for, owner, api):
    response = client_for(owner).post(
        "/api/v1/platform/organizations/",
        {
            "name": "Shivaji Nagar Mandal",
            "city": "Pune",
            "financial_year": {"label": "2027–28", "start_date": "2027-04-01", "end_date": "2028-03-31"},
            "full_name": "Raju",
            "mobile": "9123456789",
            "password": NEW_PASSWORD,
        },
        format="json",
    )
    assert response.status_code == 201, response.data
    org = Organization.objects.get(pk=response.data["id"])
    admin = User.objects.get(mobile="+919123456789")
    assert OrganizationMembership.objects.get(organization=org, user=admin).role.code == "org_admin"
    assert not OrganizationMembership.objects.filter(organization=org, user=owner).exists()
    login = api.post("/api/v1/auth/login/", {"identifier": "9123456789", "password": NEW_PASSWORD}, format="json")
    assert login.status_code == 200
    mine = client_for(admin).get("/api/v1/me/organizations/").data
    assert [row["name"] for row in mine] == ["Shivaji Nagar Mandal"]


def test_owner_suspends_organization_and_it_is_locked(client_for, make_org, owner):
    org = make_org()
    response = client_for(owner).post(f"/api/v1/platform/organizations/{org.pk}/status/", {"status": "suspended"})
    assert response.status_code == 200
    assert client_for(org.admin_user).get("/api/v1/me/organizations/").data == []
    client_for(owner).post(f"/api/v1/platform/organizations/{org.pk}/status/", {"status": "active"})
    assert len(client_for(org.admin_user).get("/api/v1/me/organizations/").data) == 1


def test_owner_resets_password_and_blocks_user(client_for, make_org, owner, api):
    org = make_org()
    client = client_for(owner)
    user = org.admin_user
    assert client.post(f"/api/v1/platform/users/{user.pk}/password/", {"password": NEW_PASSWORD}).status_code == 200
    ok = api.post("/api/v1/auth/login/", {"identifier": user.email, "password": NEW_PASSWORD}, format="json")
    assert ok.status_code == 200
    assert client.post(f"/api/v1/platform/users/{user.pk}/status/", {"is_active": False}).status_code == 200
    blocked = api.post("/api/v1/auth/login/", {"identifier": user.email, "password": NEW_PASSWORD}, format="json")
    assert blocked.status_code == 400
    assert client.post(f"/api/v1/platform/users/{owner.pk}/status/", {"is_active": False}).status_code == 422


def test_owner_confirms_account_whose_code_never_arrived(client_for, make_user, owner, api):
    user = make_user(email="stuck@example.com", verified=False)
    before = api.post("/api/v1/auth/login/", {"identifier": user.email, "password": DEFAULT_PASSWORD}, format="json")
    assert before.status_code == 403
    response = client_for(owner).post(f"/api/v1/platform/users/{user.pk}/verify/")
    assert response.status_code == 200 and response.data["is_verified"] is True
    after = api.post("/api/v1/auth/login/", {"identifier": user.email, "password": DEFAULT_PASSWORD}, format="json")
    assert after.status_code == 200


def test_admin_adding_unconfirmed_signup_sets_their_login(client_for, make_org, make_user, api):
    org = make_org()
    make_user(email="stuck@example.com", verified=False)
    client = org_client(client_for, org, org.admin_user)
    response = client.post(
        "/api/v1/members/",
        {
            "full_name": "Stuck",
            "email": "stuck@example.com",
            "password": NEW_PASSWORD,
            "role_id": _role_id(client, "collector"),
        },
        format="json",
    )
    assert response.status_code == 201 and response.data["new_login"] is True
    login = api.post(
        "/api/v1/auth/login/", {"identifier": "stuck@example.com", "password": NEW_PASSWORD}, format="json"
    )
    assert login.status_code == 200


# --- Username logins ------------------------------------------------------------
def _add_username_user(client, username="Ramesh.P", role="collector"):
    return client.post(
        "/api/v1/members/",
        {
            "full_name": "Ramesh Pawar",
            "username": username,
            "password": NEW_PASSWORD,
            "role_id": _role_id(client, role),
        },
        format="json",
    )


def test_admin_adds_username_login_without_email_or_mobile(client_for, make_org, api):
    org = make_org()
    client = org_client(client_for, org, org.admin_user)
    response = _add_username_user(client)
    assert response.status_code == 201, response.data
    assert response.data["user"]["username"] == "ramesh.p"
    assert response.data["new_login"] is True
    for identifier in ("ramesh.p", "  RAMESH.P "):
        login = api.post("/api/v1/auth/login/", {"identifier": identifier, "password": NEW_PASSWORD}, format="json")
        assert login.status_code == 200, login.data
        assert login.data["user"]["username"] == "ramesh.p"
    wrong = api.post("/api/v1/auth/login/", {"identifier": "ramesh.p", "password": "wrong-pass"}, format="json")
    assert wrong.status_code == 400


def test_username_rules_and_uniqueness(client_for, make_org):
    org = make_org()
    other = make_org("Other")
    client = org_client(client_for, org, org.admin_user)
    for bad in ("ab", "9ramesh", "ram esh", "ram@esh"):
        response = _add_username_user(client, username=bad)
        assert response.status_code == 400, bad
        assert "username" in response.data["error"]["details"], bad
    assert _add_username_user(client).status_code == 201
    other_client = org_client(client_for, other, other.admin_user)
    taken = _add_username_user(other_client, username="ramesh.p")
    assert taken.status_code == 400
    assert "username" in taken.data["error"]["details"]


def test_suspended_and_deleted_users_lose_access(client_for, make_org, api):
    org = make_org()
    client = org_client(client_for, org, org.admin_user)
    member_id = _add_username_user(client).data["id"]
    user = User.objects.get(username="ramesh.p")
    their_client = client_for(user, org)
    assert their_client.get(f"/api/v1/organizations/{org.pk}/").status_code == 200

    client.patch(f"/api/v1/members/{member_id}/", {"status": "suspended"}, format="json")
    assert their_client.get(f"/api/v1/organizations/{org.pk}/").status_code == 403
    client.patch(f"/api/v1/members/{member_id}/", {"status": "active"}, format="json")

    assert client.post(f"/api/v1/members/{member_id}/remove/").status_code == 204
    assert OrganizationMembership.objects.get(pk=member_id).status == "removed"
    assert member_id not in [m["id"] for m in client.get("/api/v1/members/").data["results"]]
    assert their_client.get(f"/api/v1/organizations/{org.pk}/").status_code == 403
    assert AuditLog.objects.filter(organization=org, entity_id=member_id, after__status="removed").exists()


def test_deleted_username_can_be_given_again_in_same_org(client_for, make_org, api):
    org = make_org()
    client = org_client(client_for, org, org.admin_user)
    member_id = _add_username_user(client).data["id"]
    client.post(f"/api/v1/members/{member_id}/remove/")
    again = client.post(
        "/api/v1/members/",
        {
            "full_name": "Ramesh K",
            "username": "ramesh.p",
            "password": "Morya-Morya-2028",
            "role_id": _role_id(client, "treasurer"),
        },
        format="json",
    )
    assert again.status_code == 201, again.data
    assert again.data["status"] == "active"
    assert again.data["role"]["code"] == "treasurer"
    login = api.post("/api/v1/auth/login/", {"identifier": "ramesh.p", "password": "Morya-Morya-2028"}, format="json")
    assert login.status_code == 200


def test_admin_cannot_delete_self_or_last_admin(client_for, make_org):
    org = make_org()
    client = org_client(client_for, org, org.admin_user)
    own = OrganizationMembership.objects.get(organization=org, user=org.admin_user)
    assert client.post(f"/api/v1/members/{own.pk}/remove/").status_code == 422
    assert OrganizationMembership.objects.get(pk=own.pk).status == "active"


def test_only_member_managers_can_delete_users(client_for, make_org, add_member):
    org = make_org()
    collector = add_member(org, "collector")
    target = add_member(org, "treasurer")
    target_id = OrganizationMembership.objects.get(organization=org, user=target).pk
    response = client_for(collector, org).post(f"/api/v1/members/{target_id}/remove/")
    assert response.status_code == 403


def test_forgot_password_for_username_sends_nothing(api):
    User.objects.create_user(full_name="Ramesh", username="ramesh.p", password=NEW_PASSWORD)
    response = api.post("/api/v1/auth/password/forgot/", {"identifier": "ramesh.p"}, format="json")
    assert response.status_code == 200
    assert "debug_code" not in response.data
