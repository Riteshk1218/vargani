"""Void and correction workflow. A receipt is never deleted: approval marks it void, keeps its number and
cancels its payment and contribution lines, all in one transaction."""

from django.db import transaction
from django.forms.models import model_to_dict
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.audit import services as audit
from apps.contributions.models import Contribution, Due
from apps.core.exceptions import BusinessRuleViolation, InvalidStateTransition
from apps.notifications import hooks as notify
from apps.payments.models import Payment

from .models import Receipt, ReceiptVoidRequest

VOID_REQUEST = "void_request"
VOID_APPROVE = "void_approve"
VOID_REJECT = "void_reject"


def request_void(receipt, *, reason, request=None, actor=None) -> ReceiptVoidRequest:
    reason = (reason or "").strip()
    if not reason:
        raise BusinessRuleViolation(_("Give a reason for voiding this receipt."))
    with transaction.atomic():
        receipt = Receipt.objects.select_for_update().get(pk=receipt.pk)
        if receipt.status != Receipt.Status.ISSUED:
            raise InvalidStateTransition(_("This receipt is already void."))
        if receipt.void_requests.filter(status=ReceiptVoidRequest.Status.PENDING).exists():
            raise InvalidStateTransition(_("A void request for this receipt is already waiting for approval."))
        void_request = ReceiptVoidRequest.objects.create(
            organization_id=receipt.organization_id,
            receipt=receipt,
            requested_by=actor,
            reason=reason,
            created_by=actor,
            updated_by=actor,
        )
        audit.record(
            request=request,
            actor=actor,
            organization=receipt.organization,
            action=VOID_REQUEST,
            entity_type="receipts.receipt",
            entity_id=receipt.pk,
            after={"receipt_number": receipt.receipt_number, "reason": reason, "request": str(void_request.pk)},
        )
        notify.void_requested(void_request, receipt, actor)
    return void_request


def _lock_pending(void_request):
    void_request = ReceiptVoidRequest.objects.select_for_update().get(pk=void_request.pk)
    if void_request.status != ReceiptVoidRequest.Status.PENDING:
        raise InvalidStateTransition()
    return void_request


def approve(void_request, *, approver_membership, note="", request=None, actor=None) -> ReceiptVoidRequest:
    # Four-eyes rule: someone else approves, except an Organization Admin (small groups may have only one).
    if void_request.requested_by_id == actor.pk and approver_membership.role.code != "org_admin":
        raise BusinessRuleViolation(_("Someone other than the requester must approve this."))
    with transaction.atomic():
        void_request = _lock_pending(void_request)
        receipt = Receipt.objects.select_for_update().get(pk=void_request.receipt_id)
        payment = Payment.objects.select_for_update().get(pk=receipt.payment_id)
        now = timezone.now()
        before = {"receipt": receipt.status, "payment": payment.status}

        receipt.status = Receipt.Status.VOID
        receipt.void_reason = void_request.reason
        receipt.voided_by = actor
        receipt.voided_at = now
        receipt.updated_by = actor
        receipt.save(update_fields=["status", "void_reason", "voided_by", "voided_at", "updated_by", "updated_at"])

        payment.status = Payment.Status.CANCELLED
        payment.status_reason = void_request.reason
        payment.status_changed_at = now
        payment.updated_by = actor
        payment.save(update_fields=["status", "status_reason", "status_changed_at", "updated_by", "updated_at"])
        payment.lines.update(status=Contribution.Status.CANCELLED, updated_by=actor, updated_at=now)
        payment.dues.update(status=Due.Status.CANCELLED, status_reason=void_request.reason, updated_at=now)

        void_request.status = ReceiptVoidRequest.Status.APPROVED
        void_request.decided_by = actor
        void_request.decided_at = now
        void_request.decision_note = note
        void_request.updated_by = actor
        void_request.save()
        audit.record(
            request=request,
            actor=actor,
            organization=receipt.organization,
            action=VOID_APPROVE,
            entity_type="receipts.receipt",
            entity_id=receipt.pk,
            before=before,
            after={
                "receipt": receipt.status,
                "payment": payment.status,
                "receipt_number": receipt.receipt_number,
                "reason": void_request.reason,
                "request": str(void_request.pk),
            },
        )
        notify.void_decided(void_request, receipt, actor, approved=True)
    return void_request


def reject(void_request, *, note="", request=None, actor=None) -> ReceiptVoidRequest:
    with transaction.atomic():
        void_request = _lock_pending(void_request)
        void_request.status = ReceiptVoidRequest.Status.REJECTED
        void_request.decided_by = actor
        void_request.decided_at = timezone.now()
        void_request.decision_note = note
        void_request.updated_by = actor
        void_request.save()
        audit.record(
            request=request,
            actor=actor,
            organization=void_request.organization,
            action=VOID_REJECT,
            entity_type="receipts.receipt",
            entity_id=void_request.receipt_id,
            after=model_to_dict(void_request, fields=["status", "decision_note"]),
        )
        notify.void_decided(void_request, void_request.receipt, actor, approved=False)
    return void_request
