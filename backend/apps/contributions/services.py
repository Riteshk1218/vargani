"""Balances (baaki): writing one off. Creating and paying them happens in payments.services.record_payment."""

from django.db import transaction
from django.utils import timezone

from apps.audit import services as audit
from apps.core.exceptions import InvalidStateTransition

from .models import Due
from .selectors import due_remaining


@transaction.atomic
def cancel_due(due, *, reason, request=None) -> Due:
    due = Due.objects.select_for_update().get(pk=due.pk)
    if due.status != Due.Status.OPEN:
        raise InvalidStateTransition()
    remaining = due_remaining(due)
    due.status = Due.Status.CANCELLED
    due.status_reason = reason
    due.updated_by = request.user if request else None
    due.save(update_fields=["status", "status_reason", "updated_by", "updated_at"])
    audit.record(
        request=request,
        organization=due.organization,
        action=audit.STATUS_CHANGE,
        entity_type="contributions.due",
        entity_id=due.pk,
        before={"status": Due.Status.OPEN, "remaining": str(remaining)},
        after={"status": due.status, "reason": reason, "at": timezone.now().isoformat()},
    )
    return due
