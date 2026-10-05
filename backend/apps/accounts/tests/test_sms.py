import io
import json

import pytest

from apps.accounts import sms


class _Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def captured(monkeypatch):
    calls = []

    def fake_urlopen(request, timeout=0):
        calls.append(request)
        return _Response(b'{"type": "success"}')

    monkeypatch.setattr(sms.urllib.request, "urlopen", fake_urlopen)
    return calls


def test_msg91_sends_the_code_through_the_dlt_template(settings, captured):
    settings.SMS_MSG91_AUTH_KEY = "key"
    settings.SMS_MSG91_TEMPLATE_ID = "tmpl"
    sms.MSG91SMSBackend().send("+919822001122", "Your verification code is 482913. It expires in 5 minutes.")
    body = json.loads(captured[0].data)
    assert captured[0].headers["Authkey"] == "key"
    assert body["template_id"] == "tmpl"
    assert body["recipients"] == [{"mobiles": "919822001122", "otp": "482913", "minutes": "5"}]


def test_msg91_reports_provider_errors(settings, monkeypatch):
    monkeypatch.setattr(
        sms.urllib.request, "urlopen", lambda r, timeout=0: _Response(b'{"type":"error","message":"bad"}')
    )
    with pytest.raises(sms.SMSError):
        sms.MSG91SMSBackend().send("+919822001122", "code 123456")


def test_twilio_sends_text(settings, captured):
    settings.SMS_TWILIO_ACCOUNT_SID = "AC1"
    settings.SMS_TWILIO_AUTH_TOKEN = "tok"
    settings.SMS_TWILIO_FROM = "+15550001111"
    sms.TwilioSMSBackend().send("+919822001122", "Your code is 482913")
    assert captured[0].full_url.endswith("/Accounts/AC1/Messages.json")
    assert b"Body=Your+code+is+482913" in captured[0].data
