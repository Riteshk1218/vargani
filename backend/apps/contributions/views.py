import django_filters
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_noop
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response

from apps.core.bulk import BulkDeleteMixin
from apps.core.dates import OrgDayFilter
from apps.core.downloads import Col, ListDownloadMixin
from apps.core.exceptions import BusinessRuleViolation, EventRequired
from apps.core.scoping import scope_money
from apps.core.tenancy import SCOPE_ALL
from apps.core.viewsets import TenantModelViewSet, TenantReadOnlyViewSet
from apps.events.models import Event
from apps.payments.models import Payment
from apps.portal import reminders

from . import selectors, services
from .models import CollectorAssignment, Contribution, ContributionType, Due
from .serializers import ContributionSerializer, ContributionTypeSerializer, DueCancelSerializer, DueSerializer


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


class ContributionViewSet(BulkDeleteMixin, ListDownloadMixin, TenantReadOnlyViewSet):
    """Contribution lines. Lines are created by recording a payment and never edited on their own; bulk-delete
    (Organization Admin) deletes the whole collection each chosen line belongs to."""

    queryset = Contribution.objects.all()
    download_title = gettext_noop("Contributions")
    download_columns = [
        Col("person_name", gettext_noop("Name")),
        Col("contribution_type_name", gettext_noop("Contribution type")),
        Col("period_month", gettext_noop("For month"), "date"),
        Col("contributed_on", gettext_noop("Date"), "date"),
        Col("fund_name", gettext_noop("Fund")),
        Col("mode", gettext_noop("Payment mode"), "mode"),
        Col("collector_name", gettext_noop("Collected by")),
        Col("status", gettext_noop("Status"), "status"),
        Col("amount", gettext_noop("Amount"), "money"),
        Col("created_at", gettext_noop("Created at"), "datetime"),
        Col("created_by_name", gettext_noop("Created by")),
    ]
    serializer_class = ContributionSerializer
    filterset_class = ContributionFilter
    search_fields = ["person__full_name", "person__mobile"]
    ordering_fields = ["contributed_on", "amount", "period_month", "created_at", "person__full_name"]
    required_permissions = {
        "list": "contributions.view",
        "retrieve": "contributions.view",
        "summary": "contributions.view",
        "bulk_delete": "records.admin_edit",
    }
    http_method_names = ["get", "post", "head", "options"]

    def bulk_delete_targets(self, rows):
        return list({row.payment_id: row.payment for row in rows}.values())

    def bulk_delete_one(self, payment):
        from apps.payments.admin_edit import delete_payment

        delete_payment(payment, request=self.request, actor=self.request.user)

    def get_base_queryset(self):
        return Contribution.objects.for_org(self.organization).select_related(
            "person", "contribution_type", "fund", "payment", "collector__user", "created_by"
        )

    def scope_queryset(self, queryset):
        if self.action in ("list", "download") and not self.request.query_params.get("status"):
            # Lines of a deleted collection leave the list, like the collection itself.
            queryset = queryset.exclude(payment__status=Payment.Status.DELETED)
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


class DueFilter(django_filters.FilterSet):
    open = django_filters.BooleanFilter(method="filter_open", label="Only balances still owed")
    date_from = OrgDayFilter(field_name="created_at")
    date_to = OrgDayFilter(field_name="created_at", end=True)

    class Meta:
        model = Due
        fields = ["event", "person", "contribution_type", "status", "collector"]

    def filter_open(self, queryset, name, value):
        if value:
            return queryset.filter(status=Due.Status.OPEN, remaining__gt=0)
        return queryset


class DueViewSet(BulkDeleteMixin, ListDownloadMixin, TenantReadOnlyViewSet):
    """Balances (baaki): money still owed on a receipt that was given before all of it came.

    Created by recording a collection with `received` below the total, paid off by collection lines with
    `due` set, and written off with POST /dues/{id}/cancel/ (admin).
    """

    queryset = Due.objects.all()
    download_title = gettext_noop("Balance due")
    download_columns = [
        Col("person_name", gettext_noop("Name")),
        Col("person_mobile", gettext_noop("Mobile")),
        Col("contribution_type_name", gettext_noop("Contribution type")),
        Col("period_month", gettext_noop("For month"), "date"),
        Col("receipt_number", gettext_noop("Receipt")),
        Col("created_at", gettext_noop("Date"), "date"),
        Col("amount", gettext_noop("Balance due"), "money"),
        Col("paid", gettext_noop("Paid"), "money"),
        Col("remaining", gettext_noop("Still owed"), "money"),
        Col("created_by_name", gettext_noop("Created by")),
    ]
    serializer_class = DueSerializer
    http_method_names = ["get", "post", "head", "options"]
    filterset_class = DueFilter
    search_fields = ["person__full_name", "person__mobile"]
    ordering_fields = ["created_at", "amount", "remaining", "period_month", "person__full_name"]
    required_permissions = {
        "list": "contributions.view",
        "retrieve": "contributions.view",
        "cancel": "records.admin_edit",
        "bulk_delete": "records.admin_edit",
    }

    def bulk_delete_one(self, due):
        services.cancel_due(due, reason=_("Deleted by admin"), request=self.request)

    def get_base_queryset(self):
        from django.db.models import OuterRef, Subquery

        from apps.receipts.models import Receipt

        receipts = Receipt.objects.filter(payment=OuterRef("payment"), status=Receipt.Status.ISSUED).values(
            "receipt_number"
        )[:1]
        return selectors.with_balance(
            Due.objects.for_org(self.organization)
            .select_related("person", "contribution_type", "collector__user", "created_by")
            .annotate(receipt_number=Subquery(receipts))
        )

    def scope_queryset(self, queryset):
        from django.db.models import Q

        scope = self.org_context.scope("contributions.view")
        if scope == SCOPE_ALL:
            return queryset
        if scope is None:
            return queryset.none()
        # Others see the balances they recorded, those of people assigned to them (so they can collect the
        # rest) and their own.
        assigned = CollectorAssignment.objects.filter(collector=self.membership, is_active=True).values("person")
        return queryset.filter(
            Q(collector=self.membership) | Q(person__in=assigned) | Q(person__user=self.request.user)
        )

    @extend_schema(request=DueCancelSerializer, responses=DueSerializer)
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Write off what is still owed (it will not be collected)."""
        serializer = DueCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        due = services.cancel_due(self.get_object(), reason=serializer.validated_data["reason"], request=request)
        return Response(DueSerializer(self.get_base_queryset().get(pk=due.pk)).data)
