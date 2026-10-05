from django.forms.models import model_to_dict
from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from apps.audit import services as audit

from .permissions import HasOrgPermission
from .tenancy import get_org_context


class TenantScopedMixin:
    """Base for every endpoint that reads or writes organization-owned data.

    - Organization comes from the validated membership (never from the request body).
    - get_queryset() always starts from Model.objects.for_org(active organization).
    - Creates/updates stamp organization and user, and write an audit entry.
    """

    permission_classes = [IsAuthenticated, HasOrgPermission]
    required_permissions: dict = {}
    audit_entity_type: str | None = None

    # --- context ------------------------------------------------------------
    def get_organization_id(self):
        return None  # header

    def get_required_permissions(self):
        action = getattr(self, "action", None) or self.request.method.lower()
        return self.required_permissions.get(action)

    @property
    def org_context(self):
        return get_org_context(self.request, self.get_organization_id())

    @property
    def organization(self):
        return self.org_context.organization

    @property
    def membership(self):
        return self.org_context.membership

    # --- queryset -----------------------------------------------------------
    def get_base_queryset(self):
        return self.queryset.model.objects.for_org(self.organization)

    def scope_queryset(self, queryset):
        return queryset

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):  # OpenAPI schema generation: no request context
            model = self.queryset.model if self.queryset is not None else self.get_serializer_class().Meta.model
            return model.objects.none()
        return self.scope_queryset(self.get_base_queryset())

    # --- writes -------------------------------------------------------------
    def get_audit_entity_type(self):
        return self.audit_entity_type or self.queryset.model._meta.label_lower

    def perform_create(self, serializer):
        user = self.request.user
        instance = serializer.save(organization=self.organization, created_by=user, updated_by=user)
        audit.record(
            request=self.request,
            organization=self.organization,
            action=audit.CREATE,
            entity_type=self.get_audit_entity_type(),
            entity_id=instance.pk,
            after=model_to_dict(instance),
        )

    def perform_update(self, serializer):
        before = model_to_dict(serializer.instance)
        instance = serializer.save(updated_by=self.request.user)
        audit.record(
            request=self.request,
            organization=self.organization,
            action=audit.UPDATE,
            entity_type=self.get_audit_entity_type(),
            entity_id=instance.pk,
            before=before,
            after=model_to_dict(instance),
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if getattr(self.request, "_org_context", None) is not None:
            context["organization"] = self.organization
        return context


class TenantModelViewSet(
    TenantScopedMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """Create/read/update without hard delete. Subclasses expose archive/void actions instead of DELETE."""

    http_method_names = ["get", "post", "patch", "head", "options"]


class TenantReadOnlyViewSet(TenantScopedMixin, viewsets.ReadOnlyModelViewSet):
    pass
