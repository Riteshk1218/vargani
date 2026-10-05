import json

from django.core.serializers.json import DjangoJSONEncoder

from apps.core.context import get_request_id

from .models import AuditLog

CREATE = "create"
UPDATE = "update"
SOFT_DELETE = "soft_delete"
STATUS_CHANGE = "status_change"
LOGIN = "login"
LOGIN_FAILED = "login_failed"
LOGOUT = "logout"
PASSWORD_CHANGE = "password_change"
ROLE_CHANGE = "role_change"
PERMISSION_CHANGE = "permission_change"
INVITE = "invite"
INVITE_ACCEPT = "invite_accept"
INVITE_REVOKE = "invite_revoke"
LOGO_CHANGE = "logo_change"

SENSITIVE_KEYS = {"password", "token_hash", "code_hash", "secret"}


class _Encoder(DjangoJSONEncoder):
    def default(self, o):
        if hasattr(o, "name") and hasattr(o, "storage"):  # FieldFile
            return o.name or None
        if hasattr(o, "pk"):
            return str(o.pk)
        return super().default(o)


def _clean(data):
    if data is None:
        return None
    cleaned = {k: v for k, v in data.items() if k not in SENSITIVE_KEYS}
    return json.loads(json.dumps(cleaned, cls=_Encoder))


def _client_ip(request):
    if request is None:
        return None
    meta = request.META
    forwarded = meta.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip() or None
    return meta.get("REMOTE_ADDR") or None


def record(
    *,
    action,
    entity_type,
    entity_id="",
    organization=None,
    request=None,
    actor=None,
    before=None,
    after=None,
    membership=None,
):
    """Write one audit row. Call inside the same transaction as the change it describes."""
    before_clean, after_clean = _clean(before), _clean(after)
    changed = []
    if before_clean is not None and after_clean is not None:
        changed = sorted(k for k in set(before_clean) | set(after_clean) if before_clean.get(k) != after_clean.get(k))
    elif after_clean is not None:
        changed = sorted(after_clean.keys())

    if actor is None and request is not None and getattr(request, "user", None) is not None:
        actor = request.user if request.user.is_authenticated else None
    if membership is None and request is not None:
        context = getattr(request, "_org_context", None)
        if context is not None and organization is not None and context.organization.pk == organization.pk:
            membership = context.membership

    return AuditLog.objects.create(
        organization=organization,
        actor_user=actor,
        actor_membership_id=membership.pk if membership else None,
        actor_role_code=membership.role.code if membership else "",
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id or ""),
        before=before_clean,
        after=after_clean,
        changed_fields=changed,
        ip=_client_ip(request),
        user_agent=(request.META.get("HTTP_USER_AGENT", "")[:300] if request is not None else ""),
        device_id=(request.META.get("HTTP_X_DEVICE_ID", "")[:100] if request is not None else ""),
        request_id=get_request_id() or "",
    )
