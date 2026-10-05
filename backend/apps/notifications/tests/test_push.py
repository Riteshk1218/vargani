import io
import json
import urllib.error

import pytest

from apps.notifications import push
from apps.notifications.models import DeviceToken
from apps.notifications.push import ConsolePushBackend, FCMPushBackend, send_push_for
from apps.notifications.services import notify

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _clear_sent():
    ConsolePushBackend.sent.clear()


def test_device_register_move_and_unregister(make_user, client_for):
    phone_owner, other = make_user(), make_user()
    response = client_for(phone_owner).post(
        "/api/v1/devices/", {"token": "fcm-token-1", "platform": "android", "app_version": "1.0.0"}, format="json"
    )
    assert response.status_code == 201
    # Re-registering the same token is an update, not a duplicate.
    assert client_for(phone_owner).post("/api/v1/devices/", {"token": "fcm-token-1"}, format="json").status_code == 200
    # A shared phone that logs in as someone else moves the token to them.
    client_for(other).post("/api/v1/devices/", {"token": "fcm-token-1"}, format="json")
    assert DeviceToken.objects.get(token="fcm-token-1").user == other
    # Only the current owner can unregister it.
    assert client_for(phone_owner).post("/api/v1/devices/unregister/", {"token": "fcm-token-1"}).data == {"removed": 0}
    assert client_for(other).post("/api/v1/devices/unregister/", {"token": "fcm-token-1"}).data == {"removed": 1}
    assert not DeviceToken.objects.get(token="fcm-token-1").is_active
    assert client_for(other).post("/api/v1/devices/", {"token": ""}, format="json").status_code == 400


def test_notifications_are_pushed_in_the_recipients_language(make_org, make_user):
    org = make_org()
    user = make_user()
    user.preferred_language = "hi"
    user.save(update_fields=["preferred_language"])
    DeviceToken.objects.create(user=user, token="phone-a")
    DeviceToken.objects.create(user=user, token="old-phone", is_active=False)
    notify(
        [user, make_user()],
        "receipt_issued",
        {"amount": "501.00", "event": "Ganeshotsav", "number": "GC-1"},
        organization=org,
        link="/app/my",
    )
    assert len(ConsolePushBackend.sent) == 1  # one active device; the user without a device gets in-app only
    message = ConsolePushBackend.sent[0]
    assert message["token"] == "phone-a"
    assert message["title"] == "आपके योगदान के लिए धन्यवाद"
    assert "501.00" in message["body"]
    assert message["data"]["type"] == "receipt_issued" and message["data"]["link"] == "/app/my"
    assert message["data"]["organization_id"] == str(org.pk)


class _Account:
    """A throwaway service account with a real RSA key, so the JWT signing path runs."""

    @staticmethod
    def write(tmp_path):
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa

        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pem = key.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
        ).decode()
        path = tmp_path / "sa.json"
        path.write_text(
            json.dumps(
                {
                    "project_id": "vargani-test",
                    "client_email": "push@vargani-test.iam.gserviceaccount.com",
                    "private_key": pem,
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            )
        )
        return path


def test_fcm_sends_and_switches_off_unregistered_tokens(make_user, settings, tmp_path, monkeypatch):
    settings.PUSH_BACKEND = "fcm"
    settings.FCM_SERVICE_ACCOUNT_FILE = str(_Account.write(tmp_path))
    FCMPushBackend._token = None
    user = make_user()
    good = DeviceToken.objects.create(user=user, token="good-token")
    gone = DeviceToken.objects.create(user=user, token="gone-token")
    calls = []

    class _Response(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def fake_urlopen(request, timeout=0):
        calls.append(request.full_url)
        if request.full_url.startswith("https://oauth2"):
            assert b"assertion=" in request.data
            return _Response(json.dumps({"access_token": "ya29.test", "expires_in": 3600}).encode())
        body = json.loads(request.data)
        assert request.headers["Authorization"] == "Bearer ya29.test"
        if body["message"]["token"] == "gone-token":
            raise urllib.error.HTTPError(
                request.full_url, 404, "Not Found", {}, io.BytesIO(b'{"status":"UNREGISTERED"}')
            )
        return _Response(b"{}")

    monkeypatch.setattr(push.urllib.request, "urlopen", fake_urlopen)
    rows = notify([user], "dues_reminder", {"amount": "500.00", "type": "Monthly", "event": "Ganeshotsav"})
    assert send_push_for([str(r.pk) for r in rows]) >= 1
    good.refresh_from_db()
    gone.refresh_from_db()
    assert good.is_active and not gone.is_active
    assert calls[0].startswith("https://oauth2.googleapis.com/token")
    assert any("projects/vargani-test/messages:send" in url for url in calls)
