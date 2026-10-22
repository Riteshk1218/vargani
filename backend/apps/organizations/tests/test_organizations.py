import pytest
from django.core import mail
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.audit.models import AuditLog
from apps.organizations.models import FinancialYear, Invitation, Organization, OrganizationMembership

pytestmark = pytest.mark.django_db


def test_creator_becomes_org_admin(client_for, make_user):
    user = make_user()
    response = client_for(user).post(
        "/api/v1/organizations/",
        {
            "name": "Shivaji Nagar Navratri Mandal",
            "city": "Pune",
            "financial_year": {"label": "2026–27", "start_date": "2026-04-01", "end_date": "2027-03-31"},
        },
        format="json",
    )
    assert response.status_code == 201, response.data
    org = Organization.objects.get(pk=response.data["id"])
    membership = OrganizationMembership.objects.get(organization=org, user=user)
    assert membership.role.code == "org_admin"
    assert FinancialYear.objects.get(organization=org).is_current
    assert AuditLog.objects.filter(organization=org, action="create", entity_type="organizations.organization").exists()
    assert AuditLog.objects.filter(organization=org, action="role_change").exists()


def test_organization_name_is_never_defaulted(client_for, make_user):
    response = client_for(make_user()).post("/api/v1/organizations/", {"name": "  "}, format="json")
    assert response.status_code == 400


def test_list_shows_only_my_organizations(client_for, make_org, make_user):
    mine = make_org("Mine")
    make_org("Not Mine")
    response = client_for(mine.admin_user).get("/api/v1/organizations/")
    assert [o["name"] for o in response.data] == ["Mine"]


def test_my_organizations_switcher_with_roles(client_for, make_org, add_member, make_user):
    ritesh = make_user(full_name="Ritesh")
    a, b, c = make_org("A"), make_org("B"), make_org("C")
    add_member(a, "org_admin", ritesh)
    add_member(b, "treasurer", ritesh)
    add_member(c, "collector", ritesh)
    response = client_for(ritesh).get("/api/v1/me/organizations/")
    roles = {row["name"]: row["role"]["code"] for row in response.data}
    assert roles == {"A": "org_admin", "B": "treasurer", "C": "collector"}
    detail = client_for(ritesh).get(f"/api/v1/me/organizations/{b.pk}/")
    assert detail.data["role"]["code"] == "treasurer"
    assert "expenses.approve" in detail.data["permissions"]
    assert "members.manage" not in detail.data["permissions"]


def test_update_profile_audited(client_for, make_org):
    org = make_org()
    response = client_for(org.admin_user).patch(f"/api/v1/organizations/{org.pk}/", {"city": "Nashik"})
    assert response.status_code == 200
    log = AuditLog.objects.filter(organization=org, action="update").latest("id")
    assert "city" in log.changed_fields


def test_logo_upload_replace_remove(client_for, make_org, png):
    org = make_org()
    client = client_for(org.admin_user)
    upload = SimpleUploadedFile("logo.jpg", png(fmt="JPEG"), content_type="image/jpeg")
    response = client.put(f"/api/v1/organizations/{org.pk}/logo/", {"logo": upload}, format="multipart")
    assert response.status_code == 200, response.data
    org.refresh_from_db()
    first_key = org.logo
    assert first_key.startswith(f"orgs/{org.pk}/logo/") and first_key.endswith(".png")
    assert response.data["logo_url"]

    upload = SimpleUploadedFile("logo.webp", png(fmt="WEBP"), content_type="image/webp")
    client.put(f"/api/v1/organizations/{org.pk}/logo/", {"logo": upload}, format="multipart")
    org.refresh_from_db()
    assert org.logo != first_key
    assert not default_storage.exists(first_key)

    response = client.delete(f"/api/v1/organizations/{org.pk}/logo/")
    assert response.status_code == 200 and response.data["logo_url"] is None


def test_logo_rejects_non_images_and_tiny_images(client_for, make_org, png):
    org = make_org()
    client = client_for(org.admin_user)
    fake = SimpleUploadedFile("logo.png", b"<script>alert(1)</script>", content_type="image/png")
    response = client.put(f"/api/v1/organizations/{org.pk}/logo/", {"logo": fake}, format="multipart")
    assert response.status_code == 415
    gif = SimpleUploadedFile("logo.gif", png(fmt="GIF"), content_type="image/gif")
    assert client.put(f"/api/v1/organizations/{org.pk}/logo/", {"logo": gif}, format="multipart").status_code == 415
    tiny = SimpleUploadedFile("logo.png", png(size=(20, 20)), content_type="image/png")
    assert client.put(f"/api/v1/organizations/{org.pk}/logo/", {"logo": tiny}, format="multipart").status_code == 400


def test_settings_validation(client_for, make_org):
    org = make_org()
    client = client_for(org.admin_user)
    response = client.patch(
        f"/api/v1/organizations/{org.pk}/settings/", {"allow_unassigned_collection": True}, format="json"
    )
    assert response.status_code == 200 and response.data["allow_unassigned_collection"] is True
    response = client.patch(
        f"/api/v1/organizations/{org.pk}/settings/", {"allow_unassigned_collection": "maybe"}, format="json"
    )
    assert response.status_code == 400


def test_financial_years(client_for, make_org):
    org = make_org()
    client = client_for(org.admin_user, org)
    response = client.post(
        "/api/v1/financial-years/", {"label": "2028–29", "start_date": "2028-04-01", "end_date": "2029-03-31"}
    )
    assert response.status_code == 201, response.data
    assert response.data["is_current"] is False  # one is already current
    overlap = client.post(
        "/api/v1/financial-years/", {"label": "X", "start_date": "2028-10-01", "end_date": "2029-09-30"}
    )
    assert overlap.status_code == 400
    duplicate = client.post(
        "/api/v1/financial-years/", {"label": "2028–29", "start_date": "2030-04-01", "end_date": "2031-03-31"}
    )
    assert duplicate.status_code == 400
    response = client.post(f"/api/v1/financial-years/{response.data['id']}/set-current/")
    assert response.status_code == 200 and response.data["is_current"]
    assert FinancialYear.objects.filter(organization=org, is_current=True).count() == 1
    response = client.post(f"/api/v1/financial-years/{response.data['id']}/close/")
    assert response.data["status"] == "closed"
    assert client.patch(f"/api/v1/financial-years/{response.data['id']}/", {"label": "Z"}).status_code == 400


def test_first_financial_year_becomes_current(client_for, make_org):
    org = make_org(with_fy=False)
    response = client_for(org.admin_user, org).post(
        "/api/v1/financial-years/", {"label": "2026–27", "start_date": "2026-04-01", "end_date": "2027-03-31"}
    )
    assert response.status_code == 201
    assert FinancialYear.objects.get(pk=response.data["id"]).is_current


def _role_id(client, code):
    return next(r["id"] for r in client.get("/api/v1/roles/").data if r["code"] == code)


def test_invitation_flow(client_for, make_org, make_user, api):
    org = make_org()
    admin = client_for(org.admin_user, org)
    response = admin.post(
        "/api/v1/invitations/",
        {"email": "Treasurer@Example.com", "full_name": "T", "role_id": _role_id(admin, "treasurer")},
    )
    assert response.status_code == 201, response.data
    token = response.data["invite_url"].rsplit("/", 1)[1]
    assert Invitation.objects.get().token_hash != token
    assert mail.outbox and token in mail.outbox[-1].body and response.data["email_sent"]

    preview = api.get(f"/api/v1/invitations/preview/{token}/")
    assert preview.data["valid"] and preview.data["role"]["code"] == "treasurer"

    stranger = make_user(email="someone-else@example.com")
    response = client_for(stranger).post("/api/v1/invitations/accept/", {"token": token})
    assert response.status_code == 400

    invitee = make_user(email="treasurer@example.com")
    response = client_for(invitee).post("/api/v1/invitations/accept/", {"token": token})
    assert response.status_code == 201, response.data
    assert OrganizationMembership.objects.get(organization=org, user=invitee).role.code == "treasurer"
    # Single use.
    assert client_for(invitee).post("/api/v1/invitations/accept/", {"token": token}).status_code == 400


def test_unverified_user_cannot_accept(client_for, make_org, make_user):
    org = make_org()
    admin = client_for(org.admin_user, org)
    token = (
        admin.post("/api/v1/invitations/", {"email": "x@example.com", "role_id": _role_id(admin, "member")})
        .data["invite_url"]
        .rsplit("/", 1)[1]
    )
    invitee = make_user(email="x@example.com", verified=False)
    assert client_for(invitee).post("/api/v1/invitations/accept/", {"token": token}).status_code == 400


def test_revoked_invitation_cannot_be_used(client_for, make_org, make_user):
    org = make_org()
    admin = client_for(org.admin_user, org)
    response = admin.post("/api/v1/invitations/", {"email": "x@example.com", "role_id": _role_id(admin, "member")})
    token = response.data["invite_url"].rsplit("/", 1)[1]
    assert admin.post(f"/api/v1/invitations/{response.data['id']}/revoke/").status_code == 200
    invitee = make_user(email="x@example.com")
    assert client_for(invitee).post("/api/v1/invitations/accept/", {"token": token}).status_code == 400


def test_role_change_is_audited_and_last_admin_protected(client_for, make_org, add_member):
    org = make_org()
    admin = client_for(org.admin_user, org)
    secretary = add_member(org, "secretary")
    membership = OrganizationMembership.objects.get(organization=org, user=secretary)
    response = admin.patch(f"/api/v1/members/{membership.pk}/", {"role_id": _role_id(admin, "treasurer")})
    assert response.status_code == 200 and response.data["role"]["code"] == "treasurer"
    log = AuditLog.objects.filter(organization=org, action="role_change", entity_id=str(membership.pk)).get()
    assert log.before["role"] == "secretary" and log.after["role"] == "treasurer"

    own = OrganizationMembership.objects.get(organization=org, user=org.admin_user)
    response = admin.patch(f"/api/v1/members/{own.pk}/", {"role_id": _role_id(admin, "member")})
    assert response.status_code == 422


def test_suspended_member_loses_access_immediately(client_for, make_org, add_member):
    org = make_org()
    secretary = add_member(org, "secretary")
    client = client_for(secretary, org)
    assert client.get("/api/v1/people/").status_code == 200
    membership = OrganizationMembership.objects.get(organization=org, user=secretary)
    client_for(org.admin_user, org).patch(f"/api/v1/members/{membership.pk}/", {"status": "suspended"})
    assert client.get("/api/v1/people/").status_code == 403


def test_invitation_is_created_when_email_cannot_be_sent(client_for, make_org, monkeypatch):
    import smtplib

    def refuse(*args, **kwargs):
        raise smtplib.SMTPSenderRefused(550, b"sender not valid", "x@example.com")

    monkeypatch.setattr("apps.accounts.tasks.send_mail", refuse)
    org = make_org()
    admin = client_for(org.admin_user, org)
    response = admin.post(
        "/api/v1/invitations/",
        {"email": "tanaji@example.com", "mobile": "8655343549", "role_id": _role_id(admin, "collector")},
    )
    assert response.status_code == 201, response.data
    assert response.data["invite_url"] and response.data["email_sent"] is False
    assert Invitation.objects.filter(email="tanaji@example.com", status="pending").exists()
