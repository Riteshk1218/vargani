from datetime import timedelta

from django.db.models import Count, Q, Sum
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.dates import org_tz
from apps.core.exceptions import EventRequired
from apps.core.permissions import HasOrgPermission
from apps.core.tenancy import SCOPE_ALL
from apps.core.viewsets import TenantReadOnlyViewSet
from apps.events.models import Event
from apps.organizations.models import OrganizationMembership
from apps.payments.models import Payment
from apps.receipts.models import Receipt

from . import assignments
from .models import CollectorAssignment
from .serializers import AssignInputSerializer, CollectorAssignmentSerializer

EVENT_PARAM = OpenApiParameter("event", OpenApiTypes.UUID, required=True)


def _money(value) -> str:
    return f"{(value or 0):.2f}"


class CollectorAssignmentViewSet(TenantReadOnlyViewSet):
    """Who collects from whom. Assign with POST /collector-assignments/bulk/, stop with /{id}/end/."""

    queryset = CollectorAssignment.objects.all()
    serializer_class = CollectorAssignmentSerializer
    filterset_fields = ["event", "collector", "person", "is_active"]
    search_fields = ["person__full_name", "person__mobile", "person__area"]
    ordering_fields = ["person__full_name", "active_from"]
    http_method_names = ["get", "post", "head", "options"]
    required_permissions = {
        "list": ("collectors.manage", "collectors.view_performance"),
        "retrieve": ("collectors.manage", "collectors.view_performance"),
        "bulk": "collectors.manage",
        "end": "collectors.manage",
    }

    def get_base_queryset(self):
        return CollectorAssignment.objects.for_org(self.organization).select_related("person", "collector__user")

    def scope_queryset(self, queryset):
        if self.org_context.scope("collectors.manage") == SCOPE_ALL:
            return queryset
        return queryset.filter(collector=self.membership)

    @extend_schema(request=AssignInputSerializer, responses=CollectorAssignmentSerializer(many=True))
    @action(detail=False, methods=["post"])
    def bulk(self, request):
        serializer = AssignInputSerializer(data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        created = assignments.assign(
            org=self.organization,
            event=data["event"],
            collector=data["collector"],
            people=data["people"],
            request=request,
            actor=request.user,
        )
        return Response(CollectorAssignmentSerializer(created, many=True).data, status=201)

    @extend_schema(request=None, responses=CollectorAssignmentSerializer)
    @action(detail=True, methods=["post"])
    def end(self, request, pk=None):
        assignment = assignments.end(self.get_object(), request=request, actor=request.user)
        return Response(CollectorAssignmentSerializer(assignment).data)


class _EventView(APIView):
    permission_classes = [IsAuthenticated, HasOrgPermission]
    permission = "collectors.view_performance"

    def get_organization_id(self):
        return None

    def get_required_permissions(self):
        return self.permission

    def get_event(self, request):
        event_id = request.query_params.get("event")
        if not event_id:
            raise EventRequired()
        event = Event.objects.for_org(request._org_context.organization).alive().filter(pk=event_id).first()
        if event is None:
            raise NotFound()
        return event


def _collector_totals(payments):
    return payments.filter(status=Payment.Status.SUCCESSFUL).aggregate(
        total=Sum("amount"),
        count=Count("id"),
        cash=Sum("amount", filter=Q(mode="cash")),
        upi=Sum("amount", filter=Q(mode="upi")),
        other=Sum("amount", filter=~Q(mode__in=["cash", "upi"])),
    )


class CollectorPerformanceView(_EventView):
    """Every user who collected or has people assigned in the event, with their totals."""

    @extend_schema(parameters=[EVENT_PARAM], responses=OpenApiTypes.OBJECT)
    def get(self, request):
        context = request._org_context
        event = self.get_event(request)
        if context.scope(self.permission) != SCOPE_ALL:
            return Response({"results": [self._row(context.membership, event)]})
        member_ids = set(
            CollectorAssignment.objects.filter(event=event, is_active=True).values_list("collector", flat=True)
        ) | set(Payment.objects.filter(event=event).exclude(collector=None).values_list("collector", flat=True))
        members = OrganizationMembership.objects.filter(pk__in=member_ids).select_related("user", "role")
        rows = sorted((self._row(m, event) for m in members), key=lambda r: -float(r["total"]))
        return Response({"results": rows})

    def _row(self, membership, event):
        totals = _collector_totals(Payment.objects.filter(event=event, collector=membership))
        return {
            "membership": str(membership.pk),
            "name": membership.user.full_name,
            "role": membership.role.name,
            "assigned": CollectorAssignment.objects.filter(event=event, collector=membership, is_active=True).count(),
            "payments": totals["count"] or 0,
            "total": _money(totals["total"]),
            "cash": _money(totals["cash"]),
            "upi": _money(totals["upi"]),
            "other": _money(totals["other"]),
        }


class MyCollectorDashboardView(_EventView):
    """The karyakarta's own numbers for the event."""

    @extend_schema(parameters=[EVENT_PARAM], responses=OpenApiTypes.OBJECT)
    def get(self, request):
        context = request._org_context
        event = self.get_event(request)
        mine = Payment.objects.filter(event=event, collector=context.membership)
        # The mandal's own calendar day, so "today" matches the app's list for today.
        now = timezone.localtime(timezone.now(), org_tz(context.organization))
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        month_start = today_start.replace(day=1)
        assigned = CollectorAssignment.objects.filter(event=event, collector=context.membership, is_active=True)
        paid_people = (
            mine.filter(status=Payment.Status.SUCCESSFUL, paid_at__gte=month_start).values("payer").distinct().count()
        )
        recent = (
            Receipt.objects.filter(payment__in=mine, status=Receipt.Status.ISSUED)
            .select_related("payment__payer")
            .order_by("-issued_at")[:10]
        )
        return Response(
            {
                "today": _money(_collector_totals(mine.filter(paid_at__gte=today_start))["total"]),
                "this_week": _money(
                    _collector_totals(mine.filter(paid_at__gte=today_start - timedelta(days=6)))["total"]
                ),
                "this_month": _money(_collector_totals(mine.filter(paid_at__gte=month_start))["total"]),
                "total": _money(_collector_totals(mine)["total"]),
                "by_mode": {k: _money(v) for k, v in _collector_totals(mine).items() if k in ("cash", "upi", "other")},
                "assigned": assigned.count(),
                "paid_this_month": paid_people,
                "pending_payments": mine.filter(status=Payment.Status.PENDING).count(),
                # Opens "my payments" (?collector=) from the cards above.
                "collector": str(context.membership.pk),
                "recent_receipts": [
                    {
                        "id": str(r.pk),
                        "receipt_number": r.receipt_number,
                        "payer_name": r.payment.payer_name,
                        "paid_at": r.payment.paid_at.isoformat(),
                        "amount": _money(r.payment.amount),
                        "issued_at": r.issued_at.isoformat(),
                    }
                    for r in recent
                ],
            }
        )
