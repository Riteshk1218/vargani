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
from apps.contributions.models import Contribution, ContributionType, Due
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
    due: Due | None = None  # this line pays (part of) an earlier balance


def _org_today(org, moment: datetime) -> date:
    try:
        tz = ZoneInfo(org.timezone)
    except Exception:  # noqa: BLE001
        tz = timezone.get_current_timezone()
    return timezone.localtime(moment, tz).date()


def _validate(*, org, event, payer, mode, status, paid_at, reference_number, amount, lines, online=False):
    if event.status != Event.Status.ACTIVE:
        raise BusinessRuleViolation(_("This event is not active. New collections are not allowed."))
    if event.financial_year.status == FinancialYear.Status.CLOSED:
        raise BusinessRuleViolation(_("This financial year is closed."))
    if payer is not None and (payer.deleted_at is not None or not payer.is_active):
        raise ValidationError({"payer": [_("This person is archived.")]})
    if (
        mode not in PaymentMode.values
        or online != (mode == PaymentMode.ONLINE)
        or (online and status != Payment.Status.PENDING)
    ):
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
        if line.due is not None:
            # Paying a balance: it is for the same type and month as the balance itself.
            line.contribution_type = line.due.contribution_type
            line.period_month = line.due.period_month
            if line.due.event_id != event.pk or payer is None or line.due.person_id != payer.pk:
                line_errors["due"] = [_("This balance belongs to another person or event.")]
            elif line.due.status != Due.Status.OPEN:
                line_errors["due"] = [_("This balance is already closed.")]
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


def _split_received(lines, received):
    """Spread the money received now over the lines in order. Returns (paid lines, unpaid parts).

    An unpaid part of a new line becomes a balance; an unpaid part of a line that pays an old balance simply
    leaves that balance open."""
    paid, unpaid = [], []
    left = received
    for line in lines:
        now = min(line.amount, left)
        left -= now
        if now > 0:
            paid.append(LineInput(line.contribution_type, now, line.period_month, line.notes, line.due))
        if line.amount - now > 0 and line.due is None:
            unpaid.append(LineInput(line.contribution_type, line.amount - now, line.period_month, line.notes))
    return paid, unpaid


def _check_due_amounts(lines):
    """A line paying a balance may not pay more than is still owed. Locks the balances while checking."""
    from apps.contributions.selectors import due_remaining

    wanted = {}
    for line in lines:
        if line.due is not None:
            wanted[line.due.pk] = wanted.get(line.due.pk, Decimal("0")) + line.amount
    if not wanted:
        return
    locked = {due.pk: due for due in Due.objects.select_for_update().filter(pk__in=wanted)}
    for due_id, amount in wanted.items():
        due = locked[due_id]
        if due.status != Due.Status.OPEN:
            raise ValidationError({"lines": [_("This balance is already closed.")]})
        if amount > due_remaining(due):
            raise ValidationError({"lines": [_("This is more than the balance still owed.")]})


def _validate_correction(old_receipt, event, status):
    from apps.receipts.models import Receipt

    if old_receipt.status != Receipt.Status.VOID:
        raise ValidationError({"replaces_receipt": [_("Only a voided receipt can be corrected.")]})
    if old_receipt.event_id != event.pk:
        raise ValidationError({"replaces_receipt": [_("The corrected receipt must be in the same event.")]})
    if old_receipt.replaced_by.exists():
        raise ValidationError({"replaces_receipt": [_("This receipt has already been corrected.")]})
    if status != Payment.Status.SUCCESSFUL:
        raise ValidationError({"status": [_("A correction must be a received payment.")]})


def create_person(*, org, event, data, collector=None, request=None, actor=None):
    """A new contributor typed in while collecting. Must run inside the payment's transaction.

    A collector who only sees assigned people gets the new person assigned to them in this event, so they find
    the person again for the next collection.
    """
    from apps.contributions.models import CollectorAssignment
    from apps.people.models import Person

    person = Person.objects.create(organization=org, created_by=actor, updated_by=actor, **data)
    audit.record(
        request=request,
        actor=actor,
        organization=org,
        action=audit.CREATE,
        entity_type="people.person",
        entity_id=person.pk,
        after=model_to_dict(person),
    )
    if collector is not None:
        CollectorAssignment.objects.create(
            organization=org,
            event=event,
            collector=collector,
            person=person,
            assigned_by=actor,
            created_by=actor,
            updated_by=actor,
        )
    return person


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
    replaces_receipt=None,
    online=False,
    gateway="",
    new_person=None,
    assign_new_person=False,
    received=None,
    follow_up_on=None,
    custom_fields=None,
    request=None,
    actor=None,
) -> tuple[Payment, bool]:
    """Record a payment with its contribution lines and, when successful, its receipt.

    `payer` may be None for an anonymous (no name) collection. `new_person` (a dict of Person fields) creates
    that person in the same transaction and records the payment against them.

    `received` is the money that came now when it is less than the total: the rest is saved as a balance
    (`Due`) for the named person and shown on the receipt, and it is paid off later by lines with `due` set.
    It may be zero, when the receipt is given and all the money comes later. `follow_up_on` is the date to go
    back for the rest; it is kept only when a balance is kept (payments/followups.py).

    `custom_fields` are the answers to the organization's own dropdowns, already checked by
    `organizations.form_studio.clean_values`.

    Returns (payment, created). A repeated idempotency key returns the original payment unchanged, so a
    collector on a flaky mobile network can safely retry.
    """
    if idempotency_key:
        existing = Payment.objects.filter(organization=org, idempotency_key=idempotency_key).first()
        if existing:
            return existing, False

    paid_at = paid_at or timezone.now()
    if replaces_receipt is not None:
        _validate_correction(replaces_receipt, event, status)
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
        online=online,
    )
    received = total if received is None else Decimal(received)
    if received < 0 or received > total:
        raise ValidationError({"received": [_("The amount received must be between zero and the total.")]})
    if received < total:
        if payer is None and not new_person:
            raise ValidationError({"received": [_("Choose the person to keep a balance for them.")]})
        if status != Payment.Status.SUCCESSFUL or online or replaces_receipt is not None:
            raise ValidationError({"received": [_("A balance can be kept only on a received collection.")]})
    paid_lines, unpaid_lines = _split_received(lines, received)
    if not paid_lines and not unpaid_lines:
        raise ValidationError({"received": [_("Nothing would be recorded.")]})
    if not unpaid_lines:
        follow_up_on = None
    elif follow_up_on is not None and follow_up_on < _org_today(org, timezone.now()):
        raise ValidationError({"follow_up_on": [_("The follow-up date cannot be in the past.")]})
    line_status = Contribution.Status.CONFIRMED if status == Payment.Status.SUCCESSFUL else Contribution.Status.PENDING
    contributed_on = _org_today(org, paid_at)

    try:
        with transaction.atomic():
            if new_person:
                payer = create_person(
                    org=org,
                    event=event,
                    data=new_person,
                    collector=collector if assign_new_person else None,
                    request=request,
                    actor=actor,
                )
            _check_due_amounts(paid_lines)
            payment = Payment.objects.create(
                organization=org,
                financial_year_id=event.financial_year_id,
                event=event,
                payer=payer,
                amount=received,
                mode=mode,
                status=status,
                paid_at=paid_at,
                reference_number=reference_number,
                cheque_bank=cheque_bank,
                cheque_date=cheque_date,
                collector=collector,
                idempotency_key=idempotency_key or None,
                gateway=gateway,
                notes=notes,
                follow_up_on=follow_up_on,
                custom_fields=custom_fields or {},
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
                        due=line.due,
                        created_by=actor,
                        updated_by=actor,
                    )
                    for line in paid_lines
                ]
            )
            Due.objects.bulk_create(
                [
                    Due(
                        organization=org,
                        financial_year_id=event.financial_year_id,
                        event=event,
                        contribution_type=line.contribution_type,
                        person=payer,
                        payment=payment,
                        period_month=line.period_month,
                        amount=line.amount,
                        collector=collector,
                        created_by=actor,
                        updated_by=actor,
                    )
                    for line in unpaid_lines
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
                            "due": str(line.due.pk) if line.due else None,
                        }
                        for line in paid_lines
                    ],
                    "balance": [
                        {"contribution_type": str(line.contribution_type.pk), "amount": str(line.amount)}
                        for line in unpaid_lines
                    ],
                },
            )
            if status == Payment.Status.SUCCESSFUL:
                issue_receipt(payment, request=request, actor=actor, replaces=replaces_receipt)
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
