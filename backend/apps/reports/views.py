from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import HasOrgPermission
from apps.core.tenancy import SCOPE_ALL
from apps.events.models import Event, EventParticipant
from apps.organizations.models import FinancialYear, OrganizationMembership
from apps.people.models import Person


class DashboardSummaryView(APIView):
    """Dashboard numbers for the active organization (and event, when given).

    Only real counts are returned. Financial totals are added with the contributions module (Phase 2);
    until then `financial` is null so clients show an empty state rather than invented numbers.
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
        return Response(data)
