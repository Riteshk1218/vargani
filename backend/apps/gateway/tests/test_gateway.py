import hashlib
import hmac
import json

import pytest

from apps.gateway.models import GatewayConfig, GatewayEvent
from apps.gateway.providers.razorpay import GatewayError, RazorpayClient
from apps.notifications.models import Notification
from apps.payments.models import Payment
from apps.payments.tests.test_payments import setup  # noqa: F401 - fixture
from apps.portal.tests.test_portal import member_client, otp_login, portal  # noqa: F401 - fixture
from apps.receipts.models import Receipt

pytestmark = pytest.mark.django_db

KEY_SECRET = "rzp_test_secret_123"
WEBHOOK_SECRET = "whsec_456"


def sign(secret, message: bytes) -> str:
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


@pytest.fixture
def online(portal, api, monkeypatch):  # noqa: F811
    s = portal
    response = s.admin.put(
        "/api/v1/gateway/config/",
        {"key_id": "rzp_test_key", "key_secret": KEY_SECRET, "webhook_secret": WEBHOOK_SECRET, "is_active": True},
        format="json",
    )
    assert response.status_code == 200, response.data
    orders = iter(f"order_{n}" for n in range(1, 100))
    monkeypatch.setattr(RazorpayClient, "create_order", lambda self, **kw: {"id": next(orders), **kw})
    s.member = member_client(api, s, otp_login(api, "9812345678"))
    return s


def start(s, amount="1100.50"):
    response = s.member.post(
        "/api/v1/portal/pay/",
        {"event": str(s.event.pk), "lines": [{"contribution_type": str(s.donation.pk), "amount": amount}]},
        format="json",
    )
    assert response.status_code == 201, response.data
    return response.data


def webhook(api, s, payload, *, secret=WEBHOOK_SECRET, event_id="evt_1"):
    body = json.dumps(payload).encode()
    return api.generic(
        "POST",
        f"/api/v1/webhooks/razorpay/{s.org.pk}/",
        body,
        content_type="application/json",
        HTTP_X_RAZORPAY_SIGNATURE=sign(secret, body),
        HTTP_X_RAZORPAY_EVENT_ID=event_id,
    )


def captured(order_id, payment_id="pay_1", amount=110050):
    entity = {"id": payment_id, "order_id": order_id, "amount": amount, "status": "captured"}
    return {"event": "payment.captured", "payload": {"payment": {"entity": entity}}}


def test_secrets_are_write_only_and_encrypted(online):
    s = online
    data = s.admin.get("/api/v1/gateway/config/").data
    assert data["has_key_secret"] and data["has_webhook_secret"] and data["is_active"]
    assert "key_secret" not in data and "webhook_secret" not in data
    assert data["webhook_url"].endswith(f"/api/v1/webhooks/razorpay/{s.org.pk}/")
    config = GatewayConfig.objects.get(organization=s.org)
    assert KEY_SECRET not in config.key_secret_encrypted and config.key_secret == KEY_SECRET
    # Members and other roles cannot read or change gateway keys.
    assert s.member.get("/api/v1/gateway/config/").status_code == 403


def test_checkout_signature_completes_payment_once(online):
    s = online
    started = start(s)
    checkout = started["checkout"]
    assert checkout["amount"] == 110050 and checkout["key"] == "rzp_test_key"
    payment = Payment.objects.get(pk=started["payment"])
    assert payment.status == "pending" and not Receipt.objects.filter(payment=payment).exists()
    # Pending online payments do not show in the member's history or count towards totals.
    assert s.member.get("/api/v1/portal/summary/").data["total_paid"] == "501.00"

    body = {"order_id": checkout["order_id"], "payment_id": "pay_1", "signature": "forged"}
    assert s.member.post("/api/v1/portal/pay/verify/", body, format="json").status_code == 400
    payment.refresh_from_db()
    assert payment.status == "pending"

    body["signature"] = sign(KEY_SECRET, f"{checkout['order_id']}|pay_1".encode())
    response = s.member.post("/api/v1/portal/pay/verify/", body, format="json")
    assert response.status_code == 200, response.data
    assert response.data["status"] == "successful"
    assert Receipt.objects.filter(payment=payment).count() == 1
    assert s.member.get("/api/v1/portal/summary/").data["total_paid"] == "1601.50"

    # The webhook for the same payment arriving afterwards changes nothing.
    assert webhook(s.admin, s, captured(checkout["order_id"])).status_code == 200
    assert Receipt.objects.filter(payment=payment).count() == 1


def test_webhook_replay_is_idempotent_and_bad_signature_rejected(online, api):
    s = online
    order = start(s)["checkout"]["order_id"]
    forged = webhook(api, s, captured(order), secret="wrong", event_id="evt_forged")
    assert forged.status_code == 400
    assert Payment.objects.get(gateway_order_id=order).status == "pending"

    first = webhook(api, s, captured(order))
    assert first.status_code == 200 and first.content == b"processed"
    replay = webhook(api, s, captured(order))
    assert replay.status_code == 200 and replay.content == b"duplicate"
    payment = Payment.objects.get(gateway_order_id=order)
    assert payment.status == "successful" and payment.gateway_payment_id == "pay_1"
    assert Receipt.objects.filter(payment=payment).count() == 1
    assert GatewayEvent.objects.filter(organization=s.org).count() == 2


def test_webhook_amount_mismatch_is_not_accepted(online, api):
    s = online
    order = start(s)["checkout"]["order_id"]
    webhook(api, s, captured(order, amount=100))
    assert Payment.objects.get(gateway_order_id=order).status == "pending"
    assert "match" in GatewayEvent.objects.get().error


def test_failed_payment_notifies_member(online, api):
    s = online
    order = start(s)["checkout"]["order_id"]
    payload = captured(order)
    payload["event"] = "payment.failed"
    webhook(api, s, payload)
    assert Payment.objects.get(gateway_order_id=order).status == "failed"
    assert Notification.objects.filter(type="online_payment_failed", recipient__mobile="+919812345678").exists()


def test_webhook_for_another_organization_does_not_touch_this_one(online, api, make_org):
    s = online
    order = start(s)["checkout"]["order_id"]
    other = make_org("Other Mandal")
    body = json.dumps(captured(order)).encode()
    response = api.generic(
        "POST",
        f"/api/v1/webhooks/razorpay/{other.pk}/",
        body,
        content_type="application/json",
        HTTP_X_RAZORPAY_SIGNATURE=sign(WEBHOOK_SECRET, body),
        HTTP_X_RAZORPAY_EVENT_ID="evt_x",
    )
    assert response.status_code == 400  # no gateway configured there
    assert Payment.objects.get(gateway_order_id=order).status == "pending"


def test_gateway_down_marks_payment_failed(online, monkeypatch):
    s = online

    def boom(self, **kw):
        raise GatewayError("timeout")

    monkeypatch.setattr(RazorpayClient, "create_order", boom)
    response = s.member.post(
        "/api/v1/portal/pay/",
        {"event": str(s.event.pk), "lines": [{"contribution_type": str(s.donation.pk), "amount": "100"}]},
        format="json",
    )
    assert response.status_code == 503
    assert Payment.objects.filter(mode="online", status="failed").count() == 1


def test_no_gateway_means_no_online_payment(portal, api):  # noqa: F811
    s = portal
    member = member_client(api, s, otp_login(api, "9812345678"))
    assert member.get("/api/v1/portal/me/").data["online_payments"] is False
    response = member.post(
        "/api/v1/portal/pay/",
        {"event": str(s.event.pk), "lines": [{"contribution_type": str(s.donation.pk), "amount": "100"}]},
        format="json",
    )
    assert response.status_code == 503
    assert not Payment.objects.filter(mode="online").exists()


def test_staff_cannot_record_online_payments_by_hand(online):
    s = online
    response = s.admin.post(
        "/api/v1/payments/",
        {
            "event": str(s.event.pk),
            "payer": str(s.ritesh.pk),
            "mode": "online",
            "lines": [{"contribution_type": str(s.donation.pk), "amount": "100"}],
        },
        format="json",
    )
    assert response.status_code == 400
