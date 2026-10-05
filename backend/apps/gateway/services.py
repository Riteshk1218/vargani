"""Online payments: pending payment + gateway order → checkout → signature check or webhook → receipt.

The payment and its contribution lines are created `pending` before the member is sent to the gateway.
They become successful (and the receipt is issued) exactly once, whichever arrives first: the checkout
callback or the webhook. Replays and duplicates change nothing.
"""

from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from rest_framework.exceptions import APIException, ValidationError

from apps.audit import services as audit
from apps.notifications.services import money, notify
from apps.payments.models import Payment, PaymentMode
from apps.payments.services import _change_status, record_payment

from .models import GatewayConfig, GatewayEvent
from .providers import client_for
from .providers.razorpay import GatewayError

PAID_EVENTS = {"payment.captured", "order.paid"}
FAILED_EVENTS = {"payment.failed"}


class GatewayUnavailable(APIException):
    status_code = 503
    default_code = "gateway_unavailable"
    default_detail = gettext_lazy(
        "Online payment is not available right now. Please try again later or pay your collector."
    )


def active_config(org) -> GatewayConfig | None:
    return GatewayConfig.objects.filter(organization=org, is_active=True).first()


def start(*, org, event, payer, lines, request=None, actor=None) -> tuple[Payment, dict]:
    config = active_config(org)
    if config is None:
        raise GatewayUnavailable()
    payment, _created = record_payment(
        org=org,
        event=event,
        payer=payer,
        mode=PaymentMode.ONLINE,
        status=Payment.Status.PENDING,
        lines=lines,
        online=True,
        gateway=config.provider,
        notes=_("Online payment"),
        request=request,
        actor=actor,
    )
    amount_paise = int((payment.amount * 100).to_integral_value())
    try:
        order = client_for(config).create_order(
            amount_paise=amount_paise,
            currency=org.currency,
            receipt=str(payment.pk),
            notes={"organization": str(org.pk), "payment": str(payment.pk)},
        )
    except GatewayError as exc:
        _change_status(
            payment,
            Payment.Status.FAILED,
            allowed_from={Payment.Status.PENDING},
            reason="gateway order failed",
            request=request,
            actor=actor,
        )
        raise GatewayUnavailable() from exc
    payment.gateway_order_id = order["id"]
    payment.save(update_fields=["gateway_order_id", "updated_at"])
    checkout = {
        "provider": config.provider,
        "key": config.key_id,
        "order_id": order["id"],
        "amount": amount_paise,
        "currency": org.currency,
        "name": org.name,
        "description": event.name,
        "prefill": {"name": payer.full_name, "contact": payer.mobile, "email": payer.email},
    }
    return payment, checkout


def _complete(payment: Payment, *, gateway_payment_id: str, amount_paise: int | None, payload: dict, actor=None):
    """Mark a pending online payment successful and issue its receipt. Safe to call more than once."""
    with transaction.atomic():
        payment = Payment.objects.select_for_update().get(pk=payment.pk)
        if payment.status == Payment.Status.SUCCESSFUL:
            return payment, False
        if payment.status != Payment.Status.PENDING:
            # e.g. marked failed after a timeout, then captured: record it for a person to look at.
            raise ValidationError({"payment": [_("This payment is no longer waiting for the gateway.")]})
        if amount_paise is not None and Decimal(amount_paise) != payment.amount * 100:
            raise ValidationError({"amount": [_("The amount paid does not match the order.")]})
        payment.gateway_payment_id = gateway_payment_id
        payment.gateway_payload = payload
        payment.reference_number = gateway_payment_id[:100]
        try:
            payment.save(update_fields=["gateway_payment_id", "gateway_payload", "reference_number", "updated_at"])
        except IntegrityError as exc:
            raise ValidationError({"payment": [_("This gateway payment was already used.")]}) from exc
        payment = _change_status(payment, Payment.Status.SUCCESSFUL, allowed_from={Payment.Status.PENDING}, actor=actor)
    return payment, True


def confirm_checkout(*, org, order_id, payment_id, signature, actor=None) -> Payment:
    """The browser/app callback after checkout. Trust comes only from the signature."""
    payment = Payment.objects.for_org(org).filter(gateway_order_id=order_id, mode=PaymentMode.ONLINE).first()
    config = active_config(org)
    if payment is None or config is None:
        raise ValidationError({"order_id": [_("Payment not found.")]})
    if not client_for(config).checkout_signature_valid(order_id=order_id, payment_id=payment_id, signature=signature):
        audit.record(
            organization=org,
            actor=actor,
            action="gateway_signature_invalid",
            entity_type="payments.payment",
            entity_id=payment.pk,
            after={"order_id": order_id},
        )
        raise ValidationError({"signature": [_("The payment could not be verified.")]})
    payment, _created = _complete(
        payment,
        gateway_payment_id=payment_id,
        amount_paise=None,
        payload={"source": "checkout", "order_id": order_id},
        actor=actor,
    )
    return payment


def handle_webhook(*, org, body: bytes, signature: str, event_id: str, payload: dict) -> str:
    """Returns "processed", "duplicate", "ignored" or "rejected"."""
    config = GatewayConfig.objects.filter(organization=org).first()
    if config is None:
        return "rejected"
    client = client_for(config)
    valid = client.webhook_signature_valid(body, signature)
    event_id = event_id or str(payload.get("id") or "")
    if not event_id:
        return "rejected"
    try:
        with transaction.atomic():
            event = GatewayEvent.objects.create(
                organization=org,
                gateway=config.provider,
                event_id=event_id,
                event_type=str(payload.get("event", ""))[:60],
                payload=payload,
                signature_valid=valid,
            )
    except IntegrityError:
        return "duplicate"
    if not valid:
        event.error = "invalid signature"
        event.save(update_fields=["error", "updated_at"])
        return "rejected"
    info = client.parse_webhook(payload)
    payment = None
    if info["order_id"]:
        payment = Payment.objects.for_org(org).filter(gateway_order_id=info["order_id"]).first()
    result = "ignored"
    try:
        if payment is not None and info["type"] in PAID_EVENTS and info["payment_id"]:
            _complete(
                payment,
                gateway_payment_id=info["payment_id"],
                amount_paise=info["amount"],
                payload={"source": "webhook", "event": event_id},
            )
            result = "processed"
        elif payment is not None and info["type"] in FAILED_EVENTS and payment.status == Payment.Status.PENDING:
            _change_status(
                payment, Payment.Status.FAILED, allowed_from={Payment.Status.PENDING}, reason=_("Online payment failed")
            )
            if payment.payer.user_id:
                notify(
                    [payment.payer.user],
                    "online_payment_failed",
                    {"amount": money(payment.amount), "event": payment.event.name},
                    organization=org,
                    entity=payment,
                    link="/app/my",
                )
            result = "processed"
    except ValidationError as exc:
        event.error = str(exc.detail)[:300]
    event.processed_at = timezone.now()
    event.save(update_fields=["error", "processed_at", "updated_at"])
    return result
