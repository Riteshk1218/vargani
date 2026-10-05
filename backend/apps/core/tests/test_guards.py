"""Structural guards: every tenant endpoint uses the tenant base class, and nothing exposes hard delete."""

import pytest
from django.urls import URLPattern, URLResolver, get_resolver

from apps.audit.models import AuditLog
from apps.core.models import TenantModel
from apps.core.viewsets import TenantScopedMixin
from apps.organizations.models import OrganizationMembership

TENANT_MODELS_WITHOUT_BASE = (OrganizationMembership, AuditLog)


def iter_patterns(patterns, prefix=""):
    for pattern in patterns:
        if isinstance(pattern, URLResolver):
            yield from iter_patterns(pattern.url_patterns, prefix + str(pattern.pattern))
        elif isinstance(pattern, URLPattern):
            yield prefix + str(pattern.pattern), pattern.callback


def api_viewsets():
    for route, callback in iter_patterns(get_resolver().url_patterns):
        if route.startswith("api/v1/") and hasattr(callback, "cls") and hasattr(callback, "actions"):
            yield route, callback


def model_of(cls):
    queryset = getattr(cls, "queryset", None)
    if queryset is not None:
        return queryset.model
    serializer = getattr(cls, "serializer_class", None)
    return getattr(getattr(serializer, "Meta", None), "model", None)


def test_every_tenant_viewset_is_tenant_scoped():
    offenders = []
    for route, callback in api_viewsets():
        model = model_of(callback.cls)
        if model is None:
            continue
        is_tenant = issubclass(model, TenantModel) or model in TENANT_MODELS_WITHOUT_BASE
        if is_tenant and not issubclass(callback.cls, TenantScopedMixin):
            offenders.append(route)
    assert not offenders


def test_no_viewset_exposes_destroy():
    offenders = [route for route, callback in api_viewsets() if "destroy" in callback.actions.values()]
    assert not offenders


@pytest.mark.django_db
def test_audit_log_is_append_only(make_org):
    from django.db import DatabaseError, transaction

    make_org()
    entry = AuditLog.objects.first()
    with pytest.raises(DatabaseError), transaction.atomic():
        AuditLog.objects.filter(pk=entry.pk).update(action="tampered")
    with pytest.raises(DatabaseError), transaction.atomic():
        AuditLog.objects.filter(pk=entry.pk).delete()
    entry.refresh_from_db()
    assert entry.action != "tampered"
