from django.forms.models import model_to_dict
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit import services as audit
from apps.core.admin_override import ADMIN_EDIT
from apps.core.exceptions import EventRequired, InvalidStateTransition
from apps.core.tenancy import SCOPE_ALL
from apps.core.viewsets import TenantModelViewSet

from .models import Event, EventParticipant
from .serializers import EventParticipantSerializer, EventSerializer
from .templates import TEMPLATES

TRANSITIONS = {
    "close": ({Event.Status.ACTIVE, Event.Status.DRAFT}, Event.Status.CLOSED),
    "reopen": ({Event.Status.CLOSED}, Event.Status.ACTIVE),
    "activate": ({Event.Status.DRAFT}, Event.Status.ACTIVE),
    "archive": ({Event.Status.CLOSED, Event.Status.DRAFT}, Event.Status.ARCHIVED),
}


class EventViewSet(TenantModelViewSet):
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    filterset_fields = ["financial_year", "status", "template"]
    search_fields = ["name", "code"]
    ordering_fields = ["start_date", "name", "created_at"]
    required_permissions = {
        "list": "events.view",
        "retrieve": "events.view",
        "create": "events.manage",
        "partial_update": "events.manage",
        "close": "events.manage",
        "reopen": "events.manage",
        "activate": "events.manage",
        "archive": "events.manage",
        "destroy": ADMIN_EDIT,
    }
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_base_queryset(self):
        return Event.objects.for_org(self.organization).alive().select_related("financial_year")

    def destroy(self, request, *args, **kwargs):
        """Organization Admin: delete an event. It disappears from every list and summary; its records stay."""
        event = self.get_object()
        before = model_to_dict(event)
        event.soft_delete(user=request.user)
        audit.record(
            request=request,
            organization=self.organization,
            action=audit.SOFT_DELETE,
            entity_type="events.event",
            entity_id=event.pk,
            before=before,
            after=model_to_dict(event),
        )
        return Response(status=204)

    def scope_queryset(self, queryset):
        if self.org_context.scope("events.view") == SCOPE_ALL:
            return queryset
        # Members see only events they take part in.
        return queryset.filter(participants__person__user=self.request.user).distinct()

    def _transition(self, request, name):
        event = self.get_object()
        allowed_from, target = TRANSITIONS[name]
        if event.status not in allowed_from:
            raise InvalidStateTransition()
        before = model_to_dict(event)
        event.status = target
        event.updated_by = request.user
        event.save(update_fields=["status", "updated_by", "updated_at"])
        audit.record(
            request=request,
            organization=self.organization,
            action=audit.STATUS_CHANGE,
            entity_type="events.event",
            entity_id=event.pk,
            before=before,
            after=model_to_dict(event),
        )
        return Response(self.get_serializer(event).data)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        return self._transition(request, "close")

    @action(detail=True, methods=["post"])
    def reopen(self, request, pk=None):
        return self._transition(request, "reopen")

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        return self._transition(request, "activate")

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        return self._transition(request, "archive")


class EventParticipantViewSet(TenantModelViewSet):
    queryset = EventParticipant.objects.all()
    serializer_class = EventParticipantSerializer
    filterset_fields = ["participation_role", "status", "person"]
    search_fields = ["person__full_name", "person__mobile"]
    ordering_fields = ["created_at", "person__full_name"]
    required_permissions = {
        "list": "events.view",
        "retrieve": "events.view",
        "create": "events.manage",
        "partial_update": "events.manage",
    }

    def get_base_queryset(self):
        return EventParticipant.objects.for_org(self.organization).select_related("person")

    def scope_queryset(self, queryset):
        if self.org_context.scope("events.view") != SCOPE_ALL:
            queryset = queryset.filter(person__user=self.request.user)
        if self.action == "list":
            event_id = self.request.query_params.get("event")
            if not event_id:
                raise EventRequired()
            queryset = queryset.filter(event_id=event_id)
        return queryset


class EventTemplateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        return Response(
            [
                {"code": code, "name": str(t["name"]), "description": str(t["description"]), "modules": t["modules"]}
                for code, t in TEMPLATES.items()
            ]
        )
