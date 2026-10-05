"""Push delivery to the mobile app.

`send_push_for` renders each notification in its recipient's language and sends it to every active device of
that user. The backend is chosen by settings.PUSH_BACKEND:

- "console" (default): logs the message. Development and tests.
- "fcm": Firebase Cloud Messaging HTTP v1, authenticated with a Google service account (standard library +
  `cryptography`, no Firebase SDK needed).

Tokens that FCM reports as unregistered are switched off so they are not tried again.
"""

import base64
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from django.utils.module_loading import import_string

from .models import DeviceToken, Notification
from .templates import render

logger = logging.getLogger(__name__)


class PushError(Exception):
    pass


class InvalidToken(PushError):
    """The device token is no longer valid (app uninstalled, token rotated)."""


class ConsolePushBackend:
    sent: list[dict] = []  # kept for tests

    def send(self, token: str, title: str, body: str, data: dict) -> None:
        ConsolePushBackend.sent.append({"token": token, "title": title, "body": body, "data": data})
        logger.info("push to %s…: %s — %s", token[:12], title, body)


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


class FCMPushBackend:
    """FCM HTTP v1. Needs FCM_SERVICE_ACCOUNT_FILE (the JSON key downloaded from Firebase)."""

    SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
    _token: tuple[str, float] | None = None

    def __init__(self):
        path = settings.FCM_SERVICE_ACCOUNT_FILE
        if not path:
            raise PushError("FCM_SERVICE_ACCOUNT_FILE is not set")
        with open(path, encoding="utf-8") as fh:
            self.account = json.load(fh)
        self.project_id = settings.FCM_PROJECT_ID or self.account["project_id"]

    def _access_token(self) -> str:
        cached = FCMPushBackend._token
        if cached and cached[1] > time.time() + 60:
            return cached[0]
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding

        now = int(time.time())
        header = _b64(json.dumps({"alg": "RS256", "typ": "JWT"}).encode())
        claims = _b64(
            json.dumps(
                {
                    "iss": self.account["client_email"],
                    "scope": self.SCOPE,
                    "aud": self.account["token_uri"],
                    "iat": now,
                    "exp": now + 3600,
                }
            ).encode()
        )
        key = serialization.load_pem_private_key(self.account["private_key"].encode(), password=None)
        signature = key.sign(f"{header}.{claims}".encode(), padding.PKCS1v15(), hashes.SHA256())
        assertion = f"{header}.{claims}.{_b64(signature)}"
        body = urllib.parse.urlencode(
            {"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": assertion}
        ).encode()
        request = urllib.request.Request(self.account["token_uri"], data=body, method="POST")
        with urllib.request.urlopen(request, timeout=15) as response:  # noqa: S310 - Google token URI
            payload = json.loads(response.read())
        FCMPushBackend._token = (payload["access_token"], time.time() + int(payload.get("expires_in", 3600)))
        return payload["access_token"]

    def send(self, token: str, title: str, body: str, data: dict) -> None:
        message = {
            "message": {
                "token": token,
                "notification": {"title": title, "body": body},
                "data": {k: str(v) for k, v in data.items()},
                "android": {"priority": "high", "notification": {"channel_id": "vargani_default"}},
            }
        }
        request = urllib.request.Request(
            f"https://fcm.googleapis.com/v1/projects/{self.project_id}/messages:send",
            data=json.dumps(message).encode(),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self._access_token()}"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=15):  # noqa: S310 - fixed FCM URL
                return
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            if exc.code == 404 or "UNREGISTERED" in detail or ("INVALID_ARGUMENT" in detail and "token" in detail):
                raise InvalidToken(detail[:200]) from exc
            raise PushError(f"FCM {exc.code}: {detail[:200]}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise PushError(str(exc)) from exc


def get_backend():
    path = {
        "console": "apps.notifications.push.ConsolePushBackend",
        "fcm": "apps.notifications.push.FCMPushBackend",
    }.get(settings.PUSH_BACKEND, settings.PUSH_BACKEND)
    return import_string(path)()


def send_push_for(notification_ids) -> int:
    """Send each notification to its recipient's active devices. Returns how many messages went out."""
    notifications = list(
        Notification.objects.filter(pk__in=notification_ids).select_related("recipient", "organization")
    )
    user_ids = {n.recipient_id for n in notifications}
    devices: dict = {}
    for device in DeviceToken.objects.filter(user_id__in=user_ids, is_active=True):
        devices.setdefault(device.user_id, []).append(device)
    if not devices:
        return 0
    backend = get_backend()
    sent = 0
    for notification in notifications:
        targets = devices.get(notification.recipient_id, [])
        if not targets:
            continue
        title, body = render(notification, notification.recipient.preferred_language)
        data = {
            "notification_id": str(notification.pk),
            "type": notification.type,
            "link": notification.link,
            "entity_type": notification.entity_type,
            "entity_id": notification.entity_id,
            "organization_id": str(notification.organization_id or ""),
        }
        for device in targets:
            try:
                backend.send(device.token, title, body, data)
                sent += 1
            except InvalidToken:
                device.is_active = False
                device.save(update_fields=["is_active", "updated_at"])
            except PushError as exc:
                logger.warning("push failed for device %s: %s", device.pk, exc)
                device.failure_count = min(device.failure_count + 1, 1000)
                device.save(update_fields=["failure_count", "updated_at"])
    return sent
