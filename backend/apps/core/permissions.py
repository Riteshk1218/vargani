from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission

from .tenancy import get_org_context


class HasOrgPermission(BasePermission):
    """Checks the view's `required_permissions[action]` against the caller's role in the active organization.

    A value may be a single code or a tuple meaning "any of these". Actions missing from the map are denied.
    """

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        context = get_org_context(request, view.get_organization_id())
        if request.method.lower() not in view.http_method_names:
            return True  # let the view answer 405 Method Not Allowed
        required = view.get_required_permissions()
        if required is None:
            raise PermissionDenied()
        if required == ():
            return True
        codes = (required,) if isinstance(required, str) else required
        if not any(context.has(code) for code in codes):
            raise PermissionDenied()
        return True
