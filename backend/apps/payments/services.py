"""Recording money. One service backs both POST /payments/ and POST /collections/ (the karyakarta flow).

A successful payment, its contribution lines and its receipt are written in one transaction: either all
exist or none do.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.db import IntegrityError, transaction
from django.forms.models import model_to_dict
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework.exceptions import ValidationError

from apps.audit import services as audit
from apps.contributions.models import Contribution, ContributionType
from apps.core.exceptions import BusinessRuleViolation, InvalidStateTransition
from apps.events.models import Event
from apps.organizations.models import FinancialYear
from apps.receipts.services import issue_receipt

from .models import Payment, PaymentMode

MANUAL_MODES = {m for m in PaymentMode.values if m != PaymentMode.ONLINE}  # online = gateway only (Phase 5)
REFERENCE_REQUIRED = {PaymentMode.CHEQUE, PaymentMode.BANK_TRANSFER}
CLOCK_SKEW = timedelta(minutes=5)


@dataclass
class LineInput:
    contribution_type: ContributionType
    amount: Decimal
    period_month: date | None = None
    notes: str = ""


def _org_today(org, moment: datetime) -> date:
    try:
        tz = ZoneInfo(org.timezone)
    except Exception:  # noqa: BLE001
        tz = timezone.get_current_timezone()
    return timezone.localtime(moment, tz).date()


def _validate(*, org, event, payer, mode, status, paid_at, reference_number, amount, lines):
    if event.status != Event.Status.ACTIVE:
        raise BusinessRuleViolation(_("This event is not active. New collections are not allowed."))
    if event.financial_year.status == FinancialYear.Status.CLOSED:
        raise BusinessRuleViolation(_("This financial year is closed."))
    if payer.deleted_at is not None or not payer.is_active:
        raise ValidationError({"payer": [_("This person is archived.")]})
    if mode not in MANUAL_MODES:
        raise ValidationError({"mode": [_("This payment mode cannot be recorded manually.")]})
    if status not in (Payment.Status.SUCCESSFUL, Payment.Status.PENDING):
        raise ValidationError({"status": [_("A new payment must be successful or pending.")]})
    if mode in REFERENCE_REQUIRED and not reference_number:
        raise ValidationError({"reference_number": [_("Enter the cheque or transaction number.")]})
    if paid_at > timezone.now() + CLOCK_SKEW:
        raise ValidationError({"paid_at": [_("Payment date cannot be in the future.")]})
    if not lines:
        raise ValidationError({"lines": [_("Add at least one contribution.")]})

    errors = {}
    for index, line in enumerate(lines):
        line_errors = {}
        ctype = line.contribution_type
        if ctype.event_id != event.pk:
            line_errors["contribution_type"] = [_("This contribution type belongs to another event.")]
        elif not ctype.is_active:
            line_errors["contribution_type"] = [_("This contribution type is archived.")]
        if line.amount <= 0:
            line_errors["amount"] = [_("Amount must be more than zero.")]
        if ctype.kind == ContributionType.Kind.RECURRING_MONTHLY:
            if line.period_month is None:
                line_errors["period_month"] = [_("Select the month this contribution is for.")]
            else:
                line.period_month = line.period_month.replace(day=1)
        else:
            line.period_month = None
        if line_errors:
            errors[str(index)] = line_errors
    if errors:
        raise ValidationError({"lines": errors})

    total = sum((line.amount for line in lines), Decimal("0"))
    if amount is not None and Decimal(amount) != total:
        raise ValidationError({"amount": [_("Amount must equal the total of the contribution lines.")]})
    return total


def record_payment(
    *,
    org,
    event,
    payer,
    mode,
    lines: list[LineInput],
    status=Payment.Status.SUCCESSFUL,
    paid_at=None,
    amount=None,
    reference_number="",
    cheque_bank="",
    cheque_date=None,
    notes="",
    collector=None,
    idempotency_key=None,
    request=None,
    actor=None,
) -> tuple[Payment, bool]:
    """Record a payment with its contribution lines and, when successful, its receipt.

    Returns (payment, created). A repeated idempotency key returns the original payment unchanged, so a
    collector on a flaky mobile network can safely retry.
    """
    if idempotency_key:
        existing = Payment.objects.filter(organization=org, idempotency_key=idempotency_key).first()
        if existing:
            return existing, False

    paid_at = paid_at or timezone.now()
    total = _validate(
        org=org,
        event=event,
        payer=payer,
        mode=mode,
        status=status,
        paid_at=paid_at,
        reference_number=reference_number,
        amount=amount,
        lines=lines,
    )
    line_status = Contribution.Status.CONFIRMED if status == Payment.Status.SUCCESSFUL else Contribution.Status.PENDING
    contributed_on = _org_today(org, paid_at)

    try:
        with transaction.atomic():
            payment = Payment.objects.create(
                organization=org,
                financial_year_id=event.financial_year_id,
                event=event,
                payer=payer,
                amount=total,
                mode=mode,
                status=status,
                paid_at=paid_at,
                reference_number=reference_number,
                cheque_bank=cheque_bank,
                cheque_date=cheque_date,
                collector=collector,
                idempotency_key=idempotency_key or None,
                notes=notes,
                created_by=actor,
                updated_by=actor,
            )
            Contribution.objects.bulk_create(
                [
                    Contribution(
                        organization=org,
                        financial_year_id=event.financial_year_id,
                        event=event,
                        fund_id=line.contribution_type.fund_id,
                        contribution_type=line.contribution_type,
                        person=payer,
                        payment=payment,
                        period_month=line.period_month,
                        amount=line.amount,
                        contributed_on=contributed_on,
                        status=line_status,
                        collector=collector,
                        notes=line.notes,
                        created_by=actor,
                        updated_by=actor,
                    )
                    for line in lines
                ]
            )
            audit.record(
                request=request,
                actor=actor,
                organization=org,
                action=audit.CREATE,
                entity_type="payments.payment",
                entity_id=payment.pk,
                after={
                    **model_to_dict(payment, exclude=["gateway_payload"]),
                    "lines": [
                        {
                            "contribution_type": str(line.contribution_type.pk),
                            "amount": str(line.amount),
                            "period_month": line.period_month.isoformat() if line.period_month else None,
                        }
                        for line in lines
                    ],
                },
            )
            if status == Payment.Status.SUCCESSFUL:
                issue_receipt(payment, request=request, actor=actor)
    except IntegrityError:
        if idempotency_key:
            existing = Payment.objects.filter(organization=org, idempotency_key=idempotency_key).first()
            if existing:
                return existing, False
        raise
    return payment, True


def _change_status(payment, target, *, allowed_from, reason="", request=None, actor=None):
    with transaction.atomic():
        payment = Payment.objects.select_for_update().get(pk=payment.pk)
        if payment.status not in allowed_from:
            raise InvalidStateTransition()
        before = model_to_dict(payment, exclude=["gateway_payload"])
        payment.status = target
        payment.status_reason = reason
        payment.status_changed_at = timezone.now()
        payment.updated_by = actor
        payment.save(update_fields=["status", "status_reason", "status_changed_at", "updated_by", "updated_at"])
        line_status = {
            Payment.Status.SUCCESSFUL: Contribution.Status.CONFIRMED,
            Payment.Status.CANCELLED: Contribution.Status.CANCELLED,
            Payment.Status.FAILED: Contribution.Status.CANCELLED,
        }[target]
        payment.lines.update(status=line_status, updated_by=actor, updated_at=timezone.now())
        audit.record(
            request=request,
            actor=actor,
            organization=payment.organization,
            action=audit.STATUS_CHANGE,
            entity_type="payments.payment",
            entity_id=payment.pk,
            before=before,
            after=model_to_dict(payment, exclude=["gateway_payload"]),
        )
        if target == Payment.Status.SUCCESSFUL:
            issue_receipt(payment, request=request, actor=actor)
    return payment


def confirm_payment(payment, *, request=None, actor=None):
    """A pending payment (e.g. a cheque) has cleared: confirm its lines and issue the receipt."""
    if payment.event.status != Event.Status.ACTIVE:
        raise BusinessRuleViolation(_("This event is not active. New collections are not allowed."))
    return _change_status(
        payment, Payment.Status.SUCCESSFUL, allowed_from={Payment.Status.PENDING}, request=request, actor=actor
    )


def cancel_payment(payment, *, reason="", request=None, actor=None):
    return _change_status(
        payment,
        Payment.Status.CANCELLED,
        allowed_from={Payment.Status.PENDING},
        reason=reason,
        request=request,
        actor=actor,
    )


def fail_payment(payment, *, reason="", request=None, actor=None):
    """E.g. a bounced cheque."""
    return _change_status(
        payment,
        Payment.Status.FAILED,
        allowed_from={Payment.Status.PENDING},
        reason=reason,
        request=request,
        actor=actor,
    )
