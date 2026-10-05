"""Resolve the active organization for a request and the caller's permissions in it.

The organization comes only from the X-Organization-ID header (or the URL for organization detail
endpoints) and is re-validated against the user's *active* membership on every request.
"""

import uuid
from dataclasses import dataclass, field

from .exceptions import NotAMember, OrganizationRequired

ORG_HEADER = "HTTP_X_ORGANIZATION_ID"

# Data scopes, narrowest last. A permission granted with a scope applies only to those rows.
SCOPE_ALL = "all"
SCOPE_OWN = "own"  # records where I am the collector
SCOPE_ASSIGNED = "assigned"  # people assigned to me
SCOPE_SELF = "self"  # my own linked person record


@dataclass
class OrgContext:
    organization: object
    membership: object
    permissions: dict[str, str] = field(default_factory=dict)

    def has(self, code: str) -> bool:
        return code in self.permissions

    def scope(self, code: str) -> str | None:
        return self.permissions.get(code)


def load_permissions(role) -> dict[str, str]:
    from apps.organizations.models import RolePermission

    return dict(RolePermission.objects.filter(role=role).values_list("permission__code", "scope"))


def get_org_context(request, org_id=None) -> OrgContext:
    cached = getattr(request, "_org_context", None)
    if cached is not None:
        return cached

    from apps.organizations.models import Organization, OrganizationMembership

    raw = org_id or request.META.get(ORG_HEADER)
    if not raw:
        raise OrganizationRequired()
    try:
        org_uuid = uuid.UUID(str(raw))
    except ValueError as exc:
        raise NotAMember() from exc

    membership = (
        OrganizationMembership.objects.select_related("organization", "role")
        .filter(
            user=request.user,
            organization_id=org_uuid,
            status=OrganizationMembership.Status.ACTIVE,
            organization__status=Organization.Status.ACTIVE,
        )
        .first()
    )
    if membership is None:
        raise NotAMember()

    context = OrgContext(membership.organization, membership, load_permissions(membership.role))
    request._org_context = context
    # From here on the database itself only shows this organization's rows (see core/rls.py).
    from .rls import activate

    activate(membership.organization_id)
    # Mark the underlying Django request, which is what TenantDatabaseMiddleware sees.
    getattr(request, "_request", request)._rls_org = membership.organization_id
    return context
