"""Create notifications. In-app rows are written straight away; push delivery (Phase 6) runs in the background."""

from django.contrib.auth import get_user_model
from django.db import transaction

from apps.core.money import indian_format
from apps.organizations.models import OrganizationMembership

from .models import Notification


def money(value) -> str:
    return indian_format(value)


def members_with_permission(org, code, *, exclude=None):
    """Active users of `org` whose role grants `code`."""
    users = (
        get_user_model()
        .objects.filter(
            memberships__organization=org,
            memberships__status=OrganizationMembership.Status.ACTIVE,
            memberships__role__permissions__code=code,
            is_active=True,
        )
        .distinct()
    )
    if exclude is not None:
        users = users.exclude(pk=getattr(exclude, "pk", exclude))
    return list(users)


def notify(users, type_, params, *, organization=None, entity=None, link=""):
    users = [u for u in users if u is not None]
    if not users:
        return []
    entity_type = entity._meta.label_lower if entity is not None else ""
    entity_id = str(entity.pk) if entity is not None else ""
    rows = Notification.objects.bulk_create(
        [
            Notification(
                organization=organization,
                recipient=user,
                type=type_,
                params=params,
                entity_type=entity_type,
                entity_id=entity_id,
                link=link,
            )
            for user in users
        ]
    )
    ids = [str(n.pk) for n in rows]

    def _push():
        from .tasks import deliver_push

        deliver_push.delay(ids)

    transaction.on_commit(_push)
    return rows
