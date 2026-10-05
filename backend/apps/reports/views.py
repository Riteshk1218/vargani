from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.contributions.models import Contribution
from apps.contributions.selectors import summarize
from apps.core.permissions import HasOrgPermission
from apps.core.tenancy import SCOPE_ALL
from apps.events.models import Event, EventParticipant
from apps.organizations.models import FinancialYear, OrganizationMembership
from apps.payments.models import Payment
from apps.people.models import Person


class DashboardSummaryView(APIView):
    """Dashboard numbers for the active organization (and event, when given).

    Only real numbers are returned. `financial` is present for roles with dashboard.view_financial and covers
    the selected event, or every event of the current financial year when no event is given. Expenses and
    other income arrive in Phase 4, so `balance` currently equals income from contributions.
    """

    permission_classes = [IsAuthenticated, HasOrgPermission]

    def get_organization_id(self):
        return None

    def get_required_permissions(self):
        return "events.view"

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        context = request._org_context
        org = context.organization
        events = Event.objects.for_org(org).alive()
        if context.scope("events.view") != SCOPE_ALL:
            events = events.filter(participants__person__user=request.user).distinct()
        data = {
            "events": {
                "total": events.count(),
                "active": events.filter(status=Event.Status.ACTIVE).count(),
            },
            "current_financial_year": None,
            "financial": None,
        }
        fy = FinancialYear.objects.for_org(org).filter(is_current=True).first()
        if fy:
            data["current_financial_year"] = {"id": str(fy.pk), "label": fy.label}
        if context.scope("people.view") == SCOPE_ALL:
            people = Person.objects.for_org(org).alive()
            data["people"] = {"total": people.count(), "active": people.filter(is_active=True).count()}
        if context.has("members.view"):
            data["members"] = {
                "total": OrganizationMembership.objects.filter(
                    organization=org, status=OrganizationMembership.Status.ACTIVE
                ).count()
            }
        event_id = request.query_params.get("event")
        if event_id:
            event = events.filter(pk=event_id).first()
            if event is None:
                from rest_framework.exceptions import NotFound

                raise NotFound()
            data["event"] = {
                "id": str(event.pk),
                "name": event.name,
                "status": event.status,
                "target_amount": str(event.target_amount) if event.target_amount is not None else None,
                "participants": EventParticipant.objects.for_org(org).filter(event=event).count()
                if context.scope("events.view") == SCOPE_ALL
                else None,
            }
        if context.has("dashboard.view_financial"):
            data["financial"] = self._financial(org, event if event_id else None, fy)
        return Response(data)

    def _financial(self, org, event, fy):
        events = Event.objects.for_org(org).alive()
        if event is not None:
            events = events.filter(pk=event.pk)
        elif fy is not None:
            events = events.filter(financial_year=fy)
        else:
            events = events.none()
        lines = Contribution.objects.for_org(org).filter(event__in=events)
        payments = Payment.objects.for_org(org).filter(event__in=events)
        data = summarize(lines, payments)
        targets = [e.target_amount for e in events if e.target_amount is not None]
        data["target_amount"] = f"{sum(targets):.2f}" if targets else None
        data["pending_payments"] = payments.filter(status=Payment.Status.PENDING).count()
        data["income"] = data["collected"]
        data["expenses"] = None
        data["balance"] = data["collected"]
        data["recent_payments"] = [
            {
                "id": str(p.pk),
                "payer_name": p.payer.full_name,
                "amount": f"{p.amount:.2f}",
                "mode": p.mode,
                "paid_at": p.paid_at.isoformat(),
                "receipt_number": next((r.receipt_number for r in p.receipts.all() if r.status == "issued"), None),
            }
            for p in payments.filter(status=Payment.Status.SUCCESSFUL)
            .select_related("payer")
            .prefetch_related("receipts")
            .order_by("-paid_at")[:5]
        ]
        return data
