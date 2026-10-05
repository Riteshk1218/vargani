import re

import pytest
from django.core import mail

from apps.accounts.models import OTPChallenge, User
from apps.accounts.sms import MemorySMSBackend
from apps.audit.models import AuditLog
from conftest import DEFAULT_PASSWORD

pytestmark = pytest.mark.django_db


def last_code_from_email():
    return re.search(r"\b(\d{6})\b", mail.outbox[-1].body).group(1)


def register(api, **overrides):
    payload = {"full_name": "Ritesh Patil", "email": "ritesh@example.com", "password": DEFAULT_PASSWORD}
    payload.update(overrides)
    return api.post("/api/v1/auth/register/", payload, format="json")


def test_no_default_accounts_exist_after_migrate():
    assert User.objects.count() == 0


def test_register_verify_login_flow(api):
    response = register(api)
    assert response.status_code == 201, response.data
    assert "debug_code" not in response.data
    assert response.data["verification"]["channel"] == "email"
    user = User.objects.get(email="ritesh@example.com")
    assert user.password != DEFAULT_PASSWORD and user.check_password(DEFAULT_PASSWORD)

    # Login before verification is refused.
    response = api.post("/api/v1/auth/login/", {"identifier": "ritesh@example.com", "password": DEFAULT_PASSWORD})
    assert response.status_code == 403
    assert response.data["error"]["code"] == "verification_required"

    response = api.post("/api/v1/auth/verify/", {"destination": "ritesh@example.com", "code": last_code_from_email()})
    assert response.status_code == 200, response.data
    assert response.data["access"] and response.data["refresh"]

    response = api.post("/api/v1/auth/login/", {"identifier": "RITESH@example.com", "password": DEFAULT_PASSWORD})
    assert response.status_code == 200
    assert AuditLog.objects.filter(actor_user=user, action="login").exists()


def test_register_with_mobile_sends_sms_and_normalises(api):
    response = register(api, email="", mobile="98123 45678")
    assert response.status_code == 201, response.data
    assert MemorySMSBackend.outbox[-1][0] == "+919812345678"
    code = re.search(r"\b(\d{6})\b", MemorySMSBackend.outbox[-1][1]).group(1)
    response = api.post("/api/v1/auth/verify/", {"destination": "9812345678", "code": code})
    assert response.status_code == 200
    response = api.post("/api/v1/auth/login/", {"identifier": "+91 98123 45678", "password": DEFAULT_PASSWORD})
    assert response.status_code == 200


def test_register_requires_identifier_and_strong_password(api):
    response = register(api, email="", mobile="")
    assert response.status_code == 400
    response = register(api, password="12345")
    assert response.status_code == 400
    assert "password" in response.data["error"]["details"]


def test_cannot_register_over_verified_account(api, make_user):
    make_user(email="taken@example.com")
    response = register(api, email="taken@example.com")
    assert response.status_code == 400
    assert response.data["error"]["code"] == "account_exists"


def test_wrong_otp_counts_attempts_and_locks(api, settings):
    register(api)
    for _ in range(settings.OTP_MAX_ATTEMPTS):
        response = api.post("/api/v1/auth/verify/", {"destination": "ritesh@example.com", "code": "000000"})
        assert response.status_code == 400
    # Even the right code fails once attempts are exhausted.
    response = api.post("/api/v1/auth/verify/", {"destination": "ritesh@example.com", "code": last_code_from_email()})
    assert response.status_code == 400
    assert OTPChallenge.objects.get().attempts == settings.OTP_MAX_ATTEMPTS


def test_otp_resend_cooldown(api):
    register(api)
    response = api.post("/api/v1/auth/verify/resend/", {"destination": "ritesh@example.com"})
    assert response.status_code == 429


def test_login_error_is_generic(api, make_user):
    make_user(email="a@example.com")
    wrong_password = api.post("/api/v1/auth/login/", {"identifier": "a@example.com", "password": "nope-nope-nope"})
    unknown_user = api.post("/api/v1/auth/login/", {"identifier": "b@example.com", "password": "nope-nope-nope"})
    assert wrong_password.status_code == unknown_user.status_code == 400
    assert wrong_password.data["error"]["message"] == unknown_user.data["error"]["message"]


def test_refresh_rotates_and_blacklists(api, make_user):
    make_user(email="a@example.com")
    tokens = api.post("/api/v1/auth/login/", {"identifier": "a@example.com", "password": DEFAULT_PASSWORD}).data
    response = api.post("/api/v1/auth/refresh/", {"refresh": tokens["refresh"]})
    assert response.status_code == 200
    assert response.data["refresh"] != tokens["refresh"]
    reused = api.post("/api/v1/auth/refresh/", {"refresh": tokens["refresh"]})
    assert reused.status_code == 401


def test_web_client_gets_httponly_refresh_cookie(api, make_user, settings):
    make_user(email="a@example.com")
    response = api.post(
        "/api/v1/auth/login/", {"identifier": "a@example.com", "password": DEFAULT_PASSWORD}, HTTP_X_CLIENT_TYPE="web"
    )
    assert "refresh" not in response.data
    cookie = response.cookies[settings.REFRESH_COOKIE_NAME]
    assert cookie["httponly"] and cookie["path"] == "/api/v1/auth/"
    # Cookie refresh needs the web client header (cross-site forms cannot send custom headers).
    assert api.post("/api/v1/auth/refresh/", {}).status_code == 400
    response = api.post("/api/v1/auth/refresh/", {}, HTTP_X_CLIENT_TYPE="web")
    assert response.status_code == 200 and response.data["access"]


def test_logout_blacklists_refresh(api, make_user):
    make_user(email="a@example.com")
    tokens = api.post("/api/v1/auth/login/", {"identifier": "a@example.com", "password": DEFAULT_PASSWORD}).data
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    assert api.post("/api/v1/auth/logout/", {"refresh": tokens["refresh"]}).status_code == 204
    api.credentials()
    assert api.post("/api/v1/auth/refresh/", {"refresh": tokens["refresh"]}).status_code == 401


def test_password_reset_revokes_existing_tokens(api, make_user):
    make_user(email="a@example.com")
    tokens = api.post("/api/v1/auth/login/", {"identifier": "a@example.com", "password": DEFAULT_PASSWORD}).data
    assert api.post("/api/v1/auth/password/forgot/", {"identifier": "a@example.com"}).status_code == 200
    response = api.post(
        "/api/v1/auth/password/reset/",
        {
            "identifier": "a@example.com",
            "code": last_code_from_email(),
            "new_password": "An0ther-Str0ng-One",
        },
    )
    assert response.status_code == 200, response.data
    assert api.post("/api/v1/auth/refresh/", {"refresh": tokens["refresh"]}).status_code == 401
    assert (
        api.post("/api/v1/auth/login/", {"identifier": "a@example.com", "password": "An0ther-Str0ng-One"}).status_code
        == 200
    )


def test_forgot_password_does_not_reveal_accounts(api):
    response = api.post("/api/v1/auth/password/forgot/", {"identifier": "nobody@example.com"})
    assert response.status_code == 200
    assert len(mail.outbox) == 0


def test_me_get_and_update_language(client_for, make_user):
    user = make_user()
    client = client_for(user)
    response = client.patch("/api/v1/me/", {"preferred_language": "mr", "email": "hacker@example.com"})
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.preferred_language == "mr"
    assert user.email != "hacker@example.com"


def test_error_messages_follow_accept_language(api):
    response = api.post(
        "/api/v1/auth/login/", {"identifier": "x@example.com", "password": "whatever-123"}, HTTP_ACCEPT_LANGUAGE="hi"
    )
    assert response.status_code == 400
    assert response.data["error"]["message"] != "Invalid login details."


def test_unauthenticated_requests_get_envelope(api):
    response = api.get("/api/v1/me/")
    assert response.status_code == 401
    assert response.data["error"]["code"] == "not_authenticated"
    assert "request_id" in response.data
