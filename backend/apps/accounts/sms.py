"""SMS delivery backends.

The only SMS Vargani sends is the one-time login/verification code. Pick a backend with SMS_BACKEND:

- apps.accounts.sms.ConsoleSMSBackend: logs the message (development).
- apps.accounts.sms.MSG91SMSBackend: MSG91 Flow API, for India. Indian operators only deliver SMS that match a
  DLT-registered template, so the text comes from your MSG91 template, filled with the code.
- apps.accounts.sms.TwilioSMSBackend: Twilio Messaging, sends the text as written (outside India, or with a
  Twilio sender registered for India).
"""

import base64
import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)


class BaseSMSBackend:
    def send(self, to: str, message: str) -> None:
        raise NotImplementedError


class ConsoleSMSBackend(BaseSMSBackend):
    """Development backend: prints the message to the server log."""

    def send(self, to, message):
        logger.warning("SMS to %s: %s", to, message)


class MemorySMSBackend(BaseSMSBackend):
    """Test backend: keeps messages in memory."""

    outbox: list[tuple[str, str]] = []

    def send(self, to, message):
        MemorySMSBackend.outbox.append((to, message))


class SMSError(Exception):
    pass


def _post(url: str, body: bytes, headers: dict) -> dict:
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=15) as response:  # noqa: S310 - fixed provider URLs
            return json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as exc:
        raise SMSError(f"{exc.code}: {exc.read()[:200]!r}") from exc
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise SMSError(str(exc)) from exc


class MSG91SMSBackend(BaseSMSBackend):
    """MSG91 Flow API. Settings: SMS_MSG91_AUTH_KEY, SMS_MSG91_TEMPLATE_ID.

    Register a DLT template such as "Your Vargani code is ##otp##. Valid for ##minutes## minutes. Do not share
    it." and create the MSG91 flow with variables `otp` and `minutes`.
    """

    URL = "https://control.msg91.com/api/v5/flow/"

    def send(self, to, message):
        code = re.search(r"\b(\d{4,8})\b", message)
        if code is None:
            raise SMSError("MSG91 backend only sends verification codes")
        body = {
            "template_id": settings.SMS_MSG91_TEMPLATE_ID,
            "short_url": "0",
            "recipients": [
                {"mobiles": to.lstrip("+"), "otp": code.group(1), "minutes": str(settings.OTP_TTL_SECONDS // 60)}
            ],
        }
        headers = {"authkey": settings.SMS_MSG91_AUTH_KEY, "Content-Type": "application/json"}
        result = _post(self.URL, json.dumps(body).encode(), headers)
        if result.get("type") == "error":
            raise SMSError(str(result.get("message"))[:200])


class TwilioSMSBackend(BaseSMSBackend):
    """Twilio Messaging. Settings: SMS_TWILIO_ACCOUNT_SID, SMS_TWILIO_AUTH_TOKEN, SMS_TWILIO_FROM."""

    def send(self, to, message):
        sid = settings.SMS_TWILIO_ACCOUNT_SID
        auth = base64.b64encode(f"{sid}:{settings.SMS_TWILIO_AUTH_TOKEN}".encode()).decode()
        body = urllib.parse.urlencode({"To": to, "From": settings.SMS_TWILIO_FROM, "Body": message}).encode()
        _post(
            f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
            body,
            {"Authorization": f"Basic {auth}", "Content-Type": "application/x-www-form-urlencoded"},
        )


def get_sms_backend() -> BaseSMSBackend:
    return import_string(settings.SMS_BACKEND)()
