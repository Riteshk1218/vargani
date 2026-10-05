"""Collector assignments: which karyakarta collects from which person in an event."""

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework.exceptions import ValidationError

from apps.audit import services as audit
from apps.core.tenancy import load_permissions
from apps.organizations.models import OrganizationMembership

from .models import CollectorAssignment

ASSIGN = "assign"
UNASSIGN = "unassign"


def can_collect(membership) -> bool:
    return membership.status == OrganizationMembership.Status.ACTIVE and "payments.create" in load_permissions(
        membership.role
    )


def is_assigned(*, membership, person, event) -> bool:
    return CollectorAssignment.objects.filter(collector=membership, person=person, event=event, is_active=True).exists()


def assign(*, org, event, collector, people, request=None, actor=None) -> list[CollectorAssignment]:
    """Assign people to a collector. A person already assigned to someone else is moved (history is kept)."""
    if collector.organization_id != org.pk or not can_collect(collector):
        raise ValidationError({"collector": [_("This user cannot collect contributions.")]})
    created = []
    now = timezone.now()
    with transaction.atomic():
        for person in people:
            current = (
                CollectorAssignment.objects.select_for_update()
                .filter(event=event, person=person, is_active=True)
                .first()
            )
            if current and current.collector_id == collector.pk:
                continue
            if current:
                current.is_active, current.active_to, current.updated_by = False, now, actor
                current.save(update_fields=["is_active", "active_to", "updated_by", "updated_at"])
            assignment = CollectorAssignment.objects.create(
                organization=org,
                event=event,
                collector=collector,
                person=person,
                assigned_by=actor,
                created_by=actor,
                updated_by=actor,
            )
            created.append(assignment)
            audit.record(
                request=request,
                actor=actor,
                organization=org,
                action=ASSIGN,
                entity_type="contributions.collectorassignment",
                entity_id=assignment.pk,
                after={
                    "event": str(event.pk),
                    "collector": str(collector.pk),
                    "person": str(person.pk),
                    "replaced": str(current.pk) if current else None,
                },
            )
    return created


def end(assignment, *, request=None, actor=None):
    if not assignment.is_active:
        return assignment
    assignment.is_active, assignment.active_to, assignment.updated_by = False, timezone.now(), actor
    assignment.save(update_fields=["is_active", "active_to", "updated_by", "updated_at"])
    audit.record(
        request=request,
        actor=actor,
        organization=assignment.organization,
        action=UNASSIGN,
        entity_type="contributions.collectorassignment",
        entity_id=assignment.pk,
    )
    return assignment
