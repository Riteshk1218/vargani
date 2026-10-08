"""Organization Admin: edit or delete a recorded collection.

Edit keeps the receipt number and rewrites the receipt to match. Delete marks the payment `deleted`, cancels
its lines and voids its receipt, so it leaves every list and total but stays in the audit log. Both lift the
money triggers for their own transaction only (core/admin_override.py).
"""

from django.db import transaction
from django.forms.models import model_to_dict
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework.exceptions import ValidationError

from apps.audit import services as audit
from apps.contributions.models import Contribution
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


def edit_payment(payment, *, data, request=None, actor=None) -> Payment:
    """`data` may hold payer (Person or None for anonymous), new_person, mode, paid_at, reference_number,
    cheque_bank, cheque_date, notes and lines (a list of payments.services.LineInput, replacing all lines)."""
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

        lines = data.get("lines")
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
