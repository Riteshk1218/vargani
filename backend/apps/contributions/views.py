import django_filters
from django.utils import timezone
from django.utils.translation import gettext as _
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response

from apps.core.exceptions import BusinessRuleViolation, EventRequired
from apps.core.scoping import scope_money
from apps.core.tenancy import SCOPE_ALL
from apps.core.viewsets import TenantModelViewSet, TenantReadOnlyViewSet
from apps.events.models import Event
from apps.payments.models import Payment
from apps.portal import reminders

from . import selectors
from .models import Contribution, ContributionType
from .serializers import ContributionSerializer, ContributionTypeSerializer


class ContributionTypeViewSet(TenantModelViewSet):
    """What people contribute towards. Archive with PATCH {"is_active": false}; never deleted."""

    queryset = ContributionType.objects.all()
    serializer_class = ContributionTypeSerializer
    filterset_fields = ["event", "fund", "kind", "is_active", "is_mandatory"]
    search_fields = ["name"]
    ordering_fields = ["name", "created_at"]
    required_permissions = {
        "list": "contribution_types.view",
        "retrieve": "contribution_types.view",
        "create": "contribution_types.manage",
        "partial_update": "contribution_types.manage",
        "outstanding": "contributions.view",
        "remind": ("notifications.send", "contributions.view"),
    }

    def get_base_queryset(self):
        return ContributionType.objects.for_org(self.organization).select_related("fund", "event")

    @extend_schema(request=None, responses=OpenApiTypes.OBJECT)
    @action(detail=True, methods=["post"])
    def remind(self, request, pk=None):
        """Remind everyone who still owes on this mandatory type: in the app if they have a login, otherwise
        a WhatsApp link for each person is returned."""
        if not self.org_context.has("notifications.send") and self.org_context.scope("contributions.view") != SCOPE_ALL:
            raise PermissionDenied()
        ctype = self.get_object()
        if not ctype.is_mandatory:
            raise BusinessRuleViolation(_("Reminders need a mandatory contribution type with an expected amount."))
        return Response(reminders.send(ctype, request=request, actor=request.user))

    @extend_schema(responses=OpenApiTypes.OBJECT)
    @action(detail=True, methods=["get"])
    def outstanding(self, request, pk=None):
        """Dues for a mandatory type: expected per participant vs confirmed contributions."""
        if self.org_context.scope("contributions.view") != SCOPE_ALL:
            raise PermissionDenied()
        ctype = self.get_object()
        if not ctype.is_mandatory:
            raise BusinessRuleViolation(_("Dues are tracked only for mandatory contribution types."))
        return Response(selectors.outstanding(ctype, timezone.localdate()))


class ContributionFilter(django_filters.FilterSet):
    date_from = django_filters.DateFilter(field_name="contributed_on", lookup_expr="gte")
    date_to = django_filters.DateFilter(field_name="contributed_on", lookup_expr="lte")

    class Meta:
        model = Contribution
        fields = ["event", "person", "fund", "contribution_type", "period_month", "status", "collector", "payment"]


class ContributionViewSet(TenantReadOnlyViewSet):
    """Contribution lines. Read-only: lines are created by recording a payment and never edited or deleted."""

    queryset = Contribution.objects.all()
    serializer_class = ContributionSerializer
    filterset_class = ContributionFilter
    search_fields = ["person__full_name", "person__mobile"]
    ordering_fields = ["contributed_on", "amount", "period_month", "created_at"]
    required_permissions = {
        "list": "contributions.view",
        "retrieve": "contributions.view",
        "summary": "contributions.view",
    }

    def get_base_queryset(self):
        return Contribution.objects.for_org(self.organization).select_related(
            "person", "contribution_type", "fund", "payment", "collector__user"
        )

    def scope_queryset(self, queryset):
        return scope_money(queryset, self.org_context, "contributions.view", self.request.user)

    @extend_schema(
        parameters=[OpenApiParameter("event", OpenApiTypes.UUID, required=True)], responses=OpenApiTypes.OBJECT
    )
    @action(detail=False, methods=["get"])
    def summary(self, request):
        """Totals by type, fund, month and payment mode for one event (within the caller's scope)."""
        event_id = request.query_params.get("event")
        if not event_id:
            raise EventRequired()
        event = Event.objects.for_org(self.organization).alive().filter(pk=event_id).first()
        if event is None:
            raise NotFound()
        lines = self.get_queryset().filter(event=event)
        payments = scope_money(
            Payment.objects.for_org(self.organization).filter(event=event),
            self.org_context,
            "contributions.view",
            request.user,
            person="payer",
        )
        data = selectors.summarize(lines, payments)
        data["target_amount"] = f"{event.target_amount:.2f}" if event.target_amount is not None else None
        return Response(data)
