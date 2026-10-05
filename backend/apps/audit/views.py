import django_filters

from apps.core.tenancy import SCOPE_ALL
from apps.core.viewsets import TenantReadOnlyViewSet

from .models import AuditLog
from .serializers import AuditLogSerializer

# Entity types a Treasurer may see (financial scope). Financial modules add theirs in later phases.
FINANCIAL_ENTITY_PREFIXES = ("contributions.", "payments.", "receipts.", "expenses.", "funds.")


class AuditLogFilter(django_filters.FilterSet):
    date_from = django_filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="gte")
    date_to = django_filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="lte")

    class Meta:
        model = AuditLog
        fields = ["entity_type", "entity_id", "actor_user", "action"]


class AuditLogViewSet(TenantReadOnlyViewSet):
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    filterset_class = AuditLogFilter
    ordering_fields = ["created_at"]
    required_permissions = {"list": "audit.view", "retrieve": "audit.view"}

    def get_base_queryset(self):
        return AuditLog.objects.filter(organization=self.organization).select_related("actor_user")

    def scope_queryset(self, queryset):
        if self.org_context.scope("audit.view") == SCOPE_ALL:
            return queryset
        from django.db.models import Q

        condition = Q()
        for prefix in FINANCIAL_ENTITY_PREFIXES:
            condition |= Q(entity_type__startswith=prefix)
        return queryset.filter(condition)
