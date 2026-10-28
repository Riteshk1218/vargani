"""Organization Admin: edit or delete a recorded collection.

Edit keeps the receipt number and rewrites the receipt to match. A pavti that keeps a balance can have its line
amounts corrected (`line_amounts`): money taken off a line goes back onto that line's balance and money added
comes off it, so the pavti's full amount stays the same and only what was received and what is still owed move.

Delete marks the payment `deleted`, cancels its lines and voids its receipt, so it leaves every list and total
but stays in the audit log. Both lift the money triggers for their own transaction only
(core/admin_override.py).
"""

from decimal import Decimal

from django.db import transaction
from django.forms.models import model_to_dict
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework.exceptions import ValidationError

from apps.audit import services as audit
from apps.contributions.models import Contribution, Due
from apps.contributions.selectors import due_remaining
from apps.core.admin_override import ADMIN_DELETE_ACTION, ADMIN_EDIT_ACTION, allow_admin_changes
from apps.core.exceptions import InvalidStateTransition
from apps.receipts.models import Receipt
from apps.receipts.services import build_snapshot

from .models import Payment, PaymentMode
from .services import CLOCK_SKEW, REFERENCE_REQUIRED, _org_today, create_person

EDITABLE = {Payment.Status.SUCCESSFUL, Payment.Status.PENDING}
FIELDS = ["mode", "paid_at", "reference_number", "cheque_bank", "cheque_date", "notes"]
TEXT_FIELDS = {"reference_number", "cheque_bank", "notes"}


def _state(payment) -> dict:
    return {
        **model_to_dict(payment, exclude=["gateway_payload"]),
        "lines": [
            {
                "contribution_type": str(line.contribution_type_id),
                "amount": str(line.amount),
                "period_month": line.period_month.isoformat() if line.period_month else None,
            }
            for line in payment.lines.all().order_by("created_at")
        ],
    }


def _correct_amounts(payment, changes, actor):
    """Change the amounts of existing lines (`changes` maps line id to the new amount) and move the
    difference onto or off the matching balance on this pavti."""
    lines = {str(line.pk): line for line in payment.lines.select_for_update(of=("self",)).select_related("due")}
    unknown = [line_id for line_id in changes if line_id not in lines]
    if unknown:
        raise ValidationError({"line_amounts": [_("This line is not on this pavti.")]})
    now = timezone.now()
    for line_id, amount in changes.items():
        line = lines[line_id]
        delta = amount - line.amount
        if delta == 0:
            continue
        if line.due_id is not None:
            # This line pays a balance: paying less leaves more owed, paying more must stay within it.
            if line.due.status == Due.Status.OPEN and delta > due_remaining(line.due):
                raise ValidationError({"line_amounts": [_("This is more than the balance still owed.")]})
        else:
            due = (
                Due.objects.select_for_update()
                .filter(
                    payment=payment,
                    status=Due.Status.OPEN,
                    contribution_type_id=line.contribution_type_id,
                    period_month=line.period_month,
                )
                .first()
            )
            if due is not None:
                new_due = due.amount - delta
                settled = due.amount - due_remaining(due)
                if new_due < settled:
                    raise ValidationError({"line_amounts": [_("This is more than the balance still owed.")]})
                if new_due == 0:
                    due.status = Due.Status.CANCELLED
                    due.status_reason = _("Paid in full after a correction")
                else:
                    due.amount = new_due
                due.updated_by = actor
                due.save(update_fields=["amount", "status", "status_reason", "updated_by", "updated_at"])
        line.amount = amount
        line.updated_by = actor
        line.updated_at = now
        line.save(update_fields=["amount", "updated_by", "updated_at"])
    payment.amount = sum((line.amount for line in lines.values()), Decimal("0"))


def edit_payment(payment, *, data, request=None, actor=None) -> Payment:
    """`data` may hold payer (Person or None for anonymous), new_person, mode, paid_at, reference_number,
    cheque_bank, cheque_date, notes and either lines (a list of payments.services.LineInput, replacing all
    lines) or line_amounts (line id -> new amount, which also works on a pavti that keeps a balance)."""
    with transaction.atomic():
        allow_admin_changes()
        payment = Payment.objects.select_for_update().select_related("organization", "event").get(pk=payment.pk)
        if payment.status not in EDITABLE:
            raise InvalidStateTransition()
        before = _state(payment)
        org = payment.organization

        if data.get("new_person"):
            payment.payer = create_person(
                org=org, event=payment.event, data=data["new_person"], request=request, actor=actor
            )
        elif "payer" in data:
            payment.payer = data["payer"]
        old_mode = payment.mode
        for field in FIELDS:
            if field in data:
                value = data[field]
                setattr(payment, field, "" if value is None and field in TEXT_FIELDS else value)
        if payment.mode not in PaymentMode.values or (payment.mode == PaymentMode.ONLINE != old_mode):
            raise ValidationError({"mode": [_("This payment mode cannot be recorded manually.")]})
        if payment.mode in REFERENCE_REQUIRED and not payment.reference_number:
            raise ValidationError({"reference_number": [_("Enter the cheque or transaction number.")]})
        if payment.paid_at > timezone.now() + CLOCK_SKEW:
            raise ValidationError({"paid_at": [_("Payment date cannot be in the future.")]})

        has_balance = payment.dues.exists() or payment.lines.filter(due__isnull=False).exists()
        if has_balance and payment.payer_id is None:
            raise ValidationError({"payer": [_("This collection has a balance, so it needs the person's name.")]})
        if has_balance:
            payment.dues.update(person=payment.payer, updated_at=timezone.now())
        lines = data.get("lines")
        if lines is not None and data.get("line_amounts"):
            raise ValidationError({"lines": [_("Send either the lines or the line amounts, not both.")]})
        if data.get("line_amounts"):
            _correct_amounts(payment, data["line_amounts"], actor)
        if lines is not None and has_balance:
            raise ValidationError(
                {"lines": [_("This collection has a balance. Delete it and collect again to change the amounts.")]}
            )
        line_status = (
            Contribution.Status.CONFIRMED
            if payment.status == Payment.Status.SUCCESSFUL
            else Contribution.Status.PENDING
        )
        if lines is not None:
            errors = {}
            for index, line in enumerate(lines):
                ctype = line.contribution_type
                if ctype.event_id != payment.event_id:
                    errors[str(index)] = {"contribution_type": [_("This contribution type belongs to another event.")]}
                if ctype.kind == ctype.Kind.RECURRING_MONTHLY:
                    if line.period_month is None:
                        errors[str(index)] = {"period_month": [_("Select the month this contribution is for.")]}
                    else:
                        line.period_month = line.period_month.replace(day=1)
                else:
                    line.period_month = None
            if errors:
                raise ValidationError({"lines": errors})
            payment.lines.all().delete()
            payment.amount = sum(line.amount for line in lines)
            Contribution.objects.bulk_create(
                [
                    Contribution(
                        organization=org,
                        financial_year_id=payment.financial_year_id,
                        event_id=payment.event_id,
                        fund_id=line.contribution_type.fund_id,
                        contribution_type=line.contribution_type,
                        person=payment.payer,
                        payment=payment,
                        period_month=line.period_month,
                        amount=line.amount,
                        contributed_on=_org_today(org, payment.paid_at),
                        status=line_status,
                        collector=payment.collector,
                        notes=line.notes,
                        created_by=actor,
                        updated_by=actor,
                    )
                    for line in lines
                ]
            )
        else:
            payment.lines.update(
                person=payment.payer,
                contributed_on=_org_today(org, payment.paid_at),
                updated_by=actor,
                updated_at=timezone.now(),
            )
        payment.updated_by = actor
        payment.save()

        receipt = payment.receipts.filter(status=Receipt.Status.ISSUED).first()
        if receipt is not None:
            receipt.snapshot = build_snapshot(payment)
            receipt.updated_by = actor
            receipt.save(update_fields=["snapshot", "updated_by", "updated_at"])

        audit.record(
            request=request,
            actor=actor,
            organization=org,
            action=ADMIN_EDIT_ACTION,
            entity_type="payments.payment",
            entity_id=payment.pk,
            before=before,
            after=_state(payment),
        )
    return payment


def delete_payment(payment, *, reason="", request=None, actor=None) -> Payment:
    reason = (reason or "").strip() or _("Deleted by admin")
    with transaction.atomic():
        allow_admin_changes()
        payment = Payment.objects.select_for_update().select_related("organization").get(pk=payment.pk)
        if payment.status == Payment.Status.DELETED:
            raise InvalidStateTransition()
        before = _state(payment)
        now = timezone.now()
        payment.status = Payment.Status.DELETED
        payment.status_reason = reason
        payment.status_changed_at = now
        payment.updated_by = actor
        payment.save(update_fields=["status", "status_reason", "status_changed_at", "updated_by", "updated_at"])
        payment.lines.update(status=Contribution.Status.CANCELLED, updated_by=actor, updated_at=now)
        payment.dues.update(status=Due.Status.CANCELLED, status_reason=reason, updated_at=now)
        payment.receipts.filter(status=Receipt.Status.ISSUED).update(
            status=Receipt.Status.VOID, void_reason=reason, voided_by=actor, voided_at=now, updated_at=now
        )
        audit.record(
            request=request,
            actor=actor,
            organization=payment.organization,
            action=ADMIN_DELETE_ACTION,
            entity_type="payments.payment",
            entity_id=payment.pk,
            before=before,
            after=model_to_dict(payment, exclude=["gateway_payload"]),
        )
    return payment
