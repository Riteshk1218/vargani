import re
from decimal import Decimal

import pytest

from apps.accounts.models import User
from apps.accounts.sms import MemorySMSBackend
from apps.contributions.models import ContributionType
from apps.events.models import EventParticipant
from apps.notifications.models import Notification
from apps.payments.tests.test_payments import collect, setup  # noqa: F401 - fixture
from apps.people.models import Person
from apps.receipts.models import Receipt

pytestmark = pytest.mark.django_db


@pytest.fixture
def portal(setup):  # noqa: F811
    s = setup
    s.org.settings["member_portal_enabled"] = True
    s.org.save(update_fields=["settings"])
    s.suresh = Person.objects.create(organization=s.org, full_name="Suresh More", mobile="+919800000001")
    collect(s.admin, s, [{"contribution_type": str(s.donation.pk), "amount": "501"}])
    collect(s.admin, s, [{"contribution_type": str(s.donation.pk), "amount": "251"}], payer=s.suresh)
    return s


def otp_login(api, mobile):
    response = api.post("/api/v1/auth/otp/request/", {"mobile": mobile})
    assert response.status_code == 200, response.data
    code = re.search(r"\b(\d{6})\b", MemorySMSBackend.outbox[-1][1]).group(1)
    response = api.post("/api/v1/auth/otp/verify/", {"mobile": mobile, "code": code}, HTTP_X_CLIENT_TYPE="app")
    assert response.status_code == 200, response.data
    return response.data


def member_client(api, s, data):
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {data['access']}", HTTP_X_ORGANIZATION_ID=str(s.org.pk))
    return api


def test_member_otp_login_links_and_shows_only_own_data(api, portal):
    s = portal
    data = otp_login(api, "98123 45678")
    user = User.objects.get(mobile="+919812345678")
    assert user.full_name == "Ritesh Patil"
    s.ritesh.refresh_from_db()
    assert s.ritesh.user_id == user.pk
    client = member_client(api, s, data)

    me = client.get("/api/v1/portal/me/").data
    assert me["person"]["full_name"] == "Ritesh Patil"
    summary = client.get("/api/v1/portal/summary/").data
    assert summary["total_paid"] == "501.00" and summary["payments"] == 1
    receipts = client.get("/api/v1/portal/receipts/").data
    assert [r["payer_name"] for r in receipts] == ["Ritesh Patil"]
    assert len(client.get("/api/v1/portal/payments/").data) == 1

    mine = Receipt.objects.get(payment__payer=s.ritesh)
    other = Receipt.objects.get(payment__payer=s.suresh)
    assert client.get(f"/api/v1/portal/receipts/{mine.pk}/").status_code == 200
    pdf = client.get(f"/api/v1/portal/receipts/{mine.pk}/pdf/")
    assert pdf.status_code == 200 and pdf["Content-Type"] == "application/pdf"
    # Guessing another member's receipt id answers 404, as if it does not exist.
    assert client.get(f"/api/v1/portal/receipts/{other.pk}/").status_code == 404
    assert client.get(f"/api/v1/portal/receipts/{other.pk}/pdf/").status_code == 404
    # A member cannot use staff endpoints.
    assert client.get("/api/v1/payments/").status_code == 403
    assert client.get(f"/api/v1/receipts/{other.pk}/").status_code in (403, 404)


def test_shared_family_phone_is_never_linked_automatically(api, portal):
    s = portal
    Person.objects.create(organization=s.org, full_name="Sunita Patil", mobile="+919812345678")
    data = otp_login(api, "9812345678")
    assert not Person.objects.filter(organization=s.org, user__isnull=False).exists()
    client = member_client(api, s, data)
    assert client.get("/api/v1/portal/me/").status_code in (403, 404)


def test_admin_links_a_login_by_hand(api, portal, make_user, add_member):
    s = portal
    Person.objects.create(organization=s.org, full_name="Sunita Patil", mobile="+919812345678")
    member = add_member(s.org, "member", make_user(full_name="Ritesh", mobile="+919812345678"))
    response = s.admin.post(f"/api/v1/people/{s.ritesh.pk}/link-user/", {"user": str(member.pk)}, format="json")
    assert response.status_code == 200, response.data
    assert response.data["linked_user"] == str(member.pk)
    # The same login cannot be linked to a second person in the organization.
    sunita = Person.objects.get(full_name="Sunita Patil")
    response = s.admin.post(f"/api/v1/people/{sunita.pk}/link-user/", {"user": str(member.pk)}, format="json")
    assert response.status_code == 400
    # A user who is not part of the organization cannot be linked.
    outsider = make_user()
    response = s.admin.post(f"/api/v1/people/{sunita.pk}/link-user/", {"user": str(outsider.pk)}, format="json")
    assert response.status_code == 400
    assert s.admin.post(f"/api/v1/people/{s.ritesh.pk}/unlink-user/").status_code == 200
    s.ritesh.refresh_from_db()
    assert s.ritesh.user_id is None


def test_portal_switched_off_sends_no_code_to_unknown_numbers(api, setup):  # noqa: F811
    response = api.post("/api/v1/auth/otp/request/", {"mobile": "9812345678"})
    assert response.status_code == 200
    assert MemorySMSBackend.outbox == []


def test_portal_switched_off_hides_portal(api, portal):
    s = portal
    data = otp_login(api, "9812345678")
    s.org.settings["member_portal_enabled"] = False
    s.org.save(update_fields=["settings"])
    response = member_client(api, s, data).get("/api/v1/portal/me/")
    assert response.status_code == 403 and response.data["error"]["code"] == "portal_unavailable"


def test_dues_reminders_in_app_and_whatsapp(api, portal):
    s = portal
    ctype = ContributionType.objects.create(
        organization=s.org, event=s.event, name="Varshik Vargani", is_mandatory=True, target_amount=Decimal("1100")
    )
    for person in (s.ritesh, s.suresh):
        EventParticipant.objects.create(organization=s.org, event=s.event, person=person)
    otp_login(api, "9812345678")  # Ritesh has a login; Suresh does not

    result = s.admin.post(f"/api/v1/contribution-types/{ctype.pk}/remind/").data
    assert result["notified"] == 1 and result["already_reminded"] == 0
    assert [w["name"] for w in result["whatsapp"]] == ["Suresh More"]
    assert result["whatsapp"][0]["whatsapp_url"].startswith("https://wa.me/919800000001?text=")
    assert result["whatsapp"][0]["due"] == "1100.00"
    notification = Notification.objects.get(type="dues_reminder")
    s.ritesh.refresh_from_db()
    assert notification.recipient == s.ritesh.user

    # Not reminded twice in the same month.
    again = s.admin.post(f"/api/v1/contribution-types/{ctype.pk}/remind/").data
    assert again["notified"] == 0 and again["already_reminded"] == 1

    # Non-mandatory types cannot be reminded.
    assert s.admin.post(f"/api/v1/contribution-types/{s.donation.pk}/remind/").status_code == 422
