import django_filters
from django.db.models import Q
from django.forms.models import model_to_dict
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.audit import services as audit
from apps.core.phone import normalize_mobile
from apps.core.tenancy import SCOPE_ALL, SCOPE_SELF
from apps.core.viewsets import TenantModelViewSet

from .models import Person, PersonType
from .serializers import PersonSerializer


class PersonFilter(django_filters.FilterSet):
    person_type = django_filters.ChoiceFilter(choices=PersonType.choices, method="filter_person_type")
    is_active = django_filters.BooleanFilter()

    class Meta:
        model = Person
        fields = ["person_type", "is_active", "area", "building"]

    def filter_person_type(self, queryset, name, value):
        return queryset.filter(person_types__contains=[value])


class PersonViewSet(TenantModelViewSet):
    queryset = Person.objects.all()
    serializer_class = PersonSerializer
    filterset_class = PersonFilter
    search_fields = ["full_name", "mobile", "alt_mobile", "email", "unit", "building", "area"]
    ordering_fields = ["full_name", "created_at", "area"]
    required_permissions = {
        "list": "people.view",
        "retrieve": "people.view",
        "create": ("people.manage", "people.create"),
        "partial_update": "people.manage",
        "archive": "people.manage",
        "check_duplicates": ("people.manage", "people.create"),
    }

    def get_base_queryset(self):
        return Person.objects.for_org(self.organization).alive()

    def scope_queryset(self, queryset):
        queryset = self._filter_assigned(queryset)
        scope = self.org_context.scope("people.view")
        if scope == SCOPE_ALL:
            return queryset
        if scope == SCOPE_SELF:
            return queryset.filter(user=self.request.user)
        # "assigned": people assigned to this collector in any event. When the organization allows collecting
        # from anyone, collectors can find everyone (they need to look up the person who is paying).
        if self.org_context.has("payments.create") and (self.organization.settings or {}).get(
            "allow_unassigned_collection"
        ):
            return queryset
        return queryset.filter(
            collector_assignments__collector=self.membership, collector_assignments__is_active=True
        ).distinct()

    def _filter_assigned(self, queryset):
        params = self.request.query_params
        if params.get("assigned_to_me") in ("1", "true"):
            mine = {"collector_assignments__collector": self.membership, "collector_assignments__is_active": True}
            if params.get("event"):
                mine["collector_assignments__event_id"] = params["event"]
            queryset = queryset.filter(**mine).distinct()
        return queryset

    def perform_create(self, serializer):
        if (
            self.org_context.scope("people.manage") != SCOPE_ALL
            and self.org_context.scope("people.create") != SCOPE_ALL
        ):
            # Collectors may quick-add a contributor only when the organization allows unassigned collection.
            if not (self.organization.settings or {}).get("allow_unassigned_collection"):
                raise PermissionDenied()
        super().perform_create(serializer)

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        person = self.get_object()
        before = model_to_dict(person)
        person.soft_delete(user=request.user)
        audit.record(
            request=request,
            organization=self.organization,
            action=audit.SOFT_DELETE,
            entity_type="people.person",
            entity_id=person.pk,
            before=before,
            after=model_to_dict(person),
        )
        return Response(self.get_serializer(person).data)

    @action(detail=False, methods=["get"], url_path="check-duplicates")
    def check_duplicates(self, request):
        """Warn (never block) when a mobile number is already used; families often share one phone."""
        try:
            mobile = normalize_mobile(request.query_params.get("mobile", ""))
        except Exception:  # noqa: BLE001
            mobile = None
        if not mobile:
            return Response({"results": []})
        matches = self.get_base_queryset().filter(Q(mobile=mobile) | Q(alt_mobile=mobile))[:10]
        return Response({"results": [{"id": str(p.pk), "full_name": p.full_name, "mobile": p.mobile} for p in matches]})
