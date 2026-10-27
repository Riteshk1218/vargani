from django.forms.models import model_to_dict
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from django.utils.translation import gettext_noop
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit import services as audit
from apps.core.downloads import Col, ListDownloadMixin
from apps.core.exceptions import BusinessRuleViolation
from apps.core.tenancy import get_org_context
from apps.core.viewsets import TenantModelViewSet, TenantReadOnlyViewSet, TenantScopedMixin

from . import form_studio, services
from .models import FinancialYear, Invitation, Organization, OrganizationMembership, Permission, Role
from .serializers import (
    FinancialYearSerializer,
    FormStudioSerializer,
    InvitationAcceptSerializer,
    InvitationSerializer,
    LogoUploadSerializer,
    MemberCreateSerializer,
    MemberSerializer,
    MyOrganizationSerializer,
    OrganizationCreateSerializer,
    OrganizationSerializer,
    OrganizationSettingsSerializer,
    PermissionSerializer,
    RoleSerializer,
    SetPasswordSerializer,
    roles_for,
)


def _my_memberships(user):
    return (
        OrganizationMembership.objects.filter(
            user=user,
            status=OrganizationMembership.Status.ACTIVE,
            organization__status=Organization.Status.ACTIVE,
        )
        .select_related("organization", "role")
        .order_by("organization__name")
    )


class OrganizationViewSet(TenantScopedMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Organizations the caller belongs to. Detail routes take the organization from the URL."""

    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    http_method_names = ["get", "post", "patch", "put", "delete", "head", "options"]
    required_permissions = {
        "retrieve": "organization.view",
        "partial_update": "organization.manage",
        "logo": "organization.manage",
        "org_settings": ("organization.view",),
        "studio": ("organization.view",),
    }
    filter_backends = []
    pagination_class = None

    def get_permissions(self):
        if self.action in ("list", "create"):
            return [IsAuthenticated()]
        return super().get_permissions()

    def get_organization_id(self):
        return self.kwargs.get("pk")

    def get_required_permissions(self):
        if self.action in ("org_settings", "studio") and self.request.method != "GET":
            return "organization.manage"
        return super().get_required_permissions()

    def get_object(self):
        return self.organization

    def get_serializer_class(self):
        if self.action == "create":
            return OrganizationCreateSerializer
        return OrganizationSerializer

    def list(self, request):
        orgs = [m.organization for m in _my_memberships(request.user)]
        return Response(OrganizationSerializer(orgs, many=True, context={"request": request}).data)

    def create(self, request):
        serializer = OrganizationCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        financial_year = data.pop("financial_year", None)
        org = services.create_organization(user=request.user, request=request, financial_year=financial_year, **data)
        return Response(OrganizationSerializer(org, context={"request": request}).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        org = self.organization
        before = model_to_dict(org)
        serializer = OrganizationSerializer(org, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        audit.record(
            request=request,
            organization=org,
            action=audit.UPDATE,
            entity_type="organizations.organization",
            entity_id=org.pk,
            before=before,
            after=model_to_dict(org),
        )
        return Response(serializer.data)

    @extend_schema(request={"multipart/form-data": LogoUploadSerializer}, responses=OrganizationSerializer)
    @action(detail=True, methods=["put", "delete"], url_path="logo")
    def logo(self, request, pk=None):
        org = self.organization
        if request.method == "DELETE":
            services.remove_logo(org, request)
        else:
            serializer = LogoUploadSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            services.set_logo(org, serializer.validated_data["logo"], request)
        return Response(OrganizationSerializer(org, context={"request": request}).data)

    @extend_schema(request=OrganizationSettingsSerializer, responses=OrganizationSettingsSerializer)
    @action(detail=True, methods=["get", "patch"], url_path="settings")
    def org_settings(self, request, pk=None):
        org = self.organization
        current = {**services.DEFAULT_SETTINGS, **(org.settings or {})}
        if request.method == "GET":
            return Response(current)
        serializer = OrganizationSettingsSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = {**current, **services.validate_settings(dict(serializer.validated_data))}
        org.settings = updated
        org.save(update_fields=["settings", "updated_at"])
        audit.record(
            request=request,
            organization=org,
            action=audit.UPDATE,
            entity_type="organizations.organization.settings",
            entity_id=org.pk,
            before=current,
            after=updated,
        )
        return Response(updated)

    @extend_schema(request=FormStudioSerializer, responses=FormStudioSerializer)
    @action(detail=True, methods=["get", "put"], url_path="form-studio")
    def studio(self, request, pk=None):
        """Admin studio: field names, payment mode dropdown and the organization's own dropdowns on Collect."""
        org = self.organization
        current = form_studio.get_config(org)
        if request.method == "GET":
            return Response(current)
        updated = form_studio.validate_config(request.data, previous=current)
        org.settings = {**(org.settings or {}), form_studio.SETTINGS_KEY: updated}
        org.save(update_fields=["settings", "updated_at"])
        audit.record(
            request=request,
            organization=org,
            action=audit.UPDATE,
            entity_type="organizations.organization.form_studio",
            entity_id=org.pk,
            before=current,
            after=updated,
        )
        return Response(updated)


class FinancialYearViewSet(TenantModelViewSet):
    queryset = FinancialYear.objects.all()
    serializer_class = FinancialYearSerializer
    filterset_fields = ["status", "is_current"]
    ordering_fields = ["start_date", "label"]
    required_permissions = {
        "list": "financial_years.view",
        "retrieve": "financial_years.view",
        "create": "financial_years.manage",
        "partial_update": "financial_years.manage",
        "set_current": "financial_years.manage",
        "close": "financial_years.manage",
    }

    def perform_create(self, serializer):
        super().perform_create(serializer)
        fy = serializer.instance
        if not FinancialYear.objects.for_org(self.organization).filter(is_current=True).exists():
            services.set_current_financial_year(fy, self.request)

    @action(detail=True, methods=["post"], url_path="set-current")
    def set_current(self, request, pk=None):
        fy = services.set_current_financial_year(self.get_object(), request)
        return Response(FinancialYearSerializer(fy).data)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        fy = services.close_financial_year(self.get_object(), request)
        return Response(FinancialYearSerializer(fy).data)


class MemberViewSet(
    ListDownloadMixin,
    TenantScopedMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Users with access to the organization. An admin can add someone directly with a login and password,
    or send an invitation link instead (see InvitationViewSet)."""

    queryset = OrganizationMembership.objects.all()
    download_title = gettext_noop("Users")
    download_columns = [
        Col("user.full_name", gettext_noop("Name")),
        Col("user.email", gettext_noop("Email")),
        Col("user.mobile", gettext_noop("Mobile")),
        Col("role.name", gettext_noop("Role")),
        Col("status", gettext_noop("Status"), "status"),
    ]
    serializer_class = MemberSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]
    filterset_fields = ["status"]
    search_fields = ["user__full_name", "user__username", "user__email", "user__mobile"]
    ordering_fields = ["joined_at"]
    required_permissions = {
        "list": "members.view",
        "retrieve": "members.view",
        "create": "members.manage",
        "partial_update": "members.manage",
        "remove": "members.manage",
        "set_password": "members.manage",
    }

    def get_base_queryset(self):
        rows = OrganizationMembership.objects.filter(organization=self.organization).select_related("user", "role")
        if self.request.query_params.get("status") != OrganizationMembership.Status.REMOVED:
            rows = rows.exclude(status=OrganizationMembership.Status.REMOVED)  # deleted users stay out of sight
        return rows

    @extend_schema(request=None, responses={204: None})
    @action(detail=True, methods=["post"])
    def remove(self, request, pk=None):
        """Delete a user's access (kept as "removed" for the records and the audit log)."""
        membership = self.get_object()
        if membership.user_id == request.user.pk:
            raise BusinessRuleViolation(_("You cannot delete your own access."))
        services.remove_member(membership, request)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def partial_update(self, request, pk=None):
        membership = self.get_object()
        serializer = self.get_serializer(membership, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        membership = services.update_membership(
            membership,
            role=serializer.validated_data.get("role"),
            status_value=serializer.validated_data.get("status"),
            can_download=serializer.validated_data.get("can_download", services.UNCHANGED),
            request=request,
        )
        return Response(self.get_serializer(membership).data)

    @extend_schema(request=MemberCreateSerializer, responses=MemberSerializer)
    def create(self, request):
        serializer = MemberCreateSerializer(data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        membership, created = services.add_member_directly(
            org=self.organization,
            role=data["role"],
            full_name=data["full_name"],
            email=data["email"],
            mobile=data["mobile"],
            username=data["username"],
            password=data["password"],
            request=request,
        )
        body = self.get_serializer(membership).data
        # False when the person already had a Vargani login: they keep their own password.
        body["new_login"] = created
        return Response(body, status=status.HTTP_201_CREATED)

    @extend_schema(request=SetPasswordSerializer, responses=OpenApiTypes.OBJECT)
    @action(detail=True, methods=["post"], url_path="set-password")
    def set_password(self, request, pk=None):
        membership = self.get_object()
        serializer = SetPasswordSerializer(data=request.data, context={"user": membership.user})
        serializer.is_valid(raise_exception=True)
        services.set_member_password(membership, serializer.validated_data["password"], request)
        return Response({"detail": "ok"})


class InvitationViewSet(
    TenantScopedMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Invitation.objects.all()
    serializer_class = InvitationSerializer
    filterset_fields = ["status"]
    required_permissions = {
        "list": "members.manage",
        "retrieve": "members.manage",
        "create": "members.manage",
        "revoke": "members.manage",
    }

    def get_base_queryset(self):
        return Invitation.objects.for_org(self.organization).select_related("role")

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invitation, token = services.create_invitation(
            org=self.organization,
            role=serializer.validated_data["role"],
            email=serializer.validated_data["email"],
            mobile=serializer.validated_data["mobile"],
            full_name=serializer.validated_data.get("full_name"),
            request=request,
        )
        data = self.get_serializer(invitation).data
        # Shown once so the admin can share it (e.g. on WhatsApp). Only a hash is stored.
        data["invite_url"] = services.invitation_link(token)
        data["email_sent"] = bool(invitation.email) and services.send_invitation_email(invitation, token)
        return Response(data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def revoke(self, request, pk=None):
        invitation = services.revoke_invitation(self.get_object(), request)
        return Response(self.get_serializer(invitation).data)


class InvitationPreviewView(APIView):
    """Public: what an invitation link is for, so the accept page can show it before login."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request, token):
        invitation = services.find_invitation(token)
        if invitation is None or invitation.status != Invitation.Status.PENDING:
            return Response({"valid": False})
        return Response(
            {
                "valid": True,
                "organization": {
                    "name": invitation.organization.name,
                    "logo_url": services.logo_url(invitation.organization, request),
                },
                "role": {"code": invitation.role.code, "name": invitation.role.name},
                "invited_email": bool(invitation.email),
                "invited_mobile": bool(invitation.mobile),
                "expires_at": invitation.expires_at,
            }
        )


class InvitationAcceptView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=InvitationAcceptSerializer, responses=MyOrganizationSerializer)
    def post(self, request):
        serializer = InvitationAcceptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        membership = services.accept_invitation(
            token=serializer.validated_data["token"], user=request.user, request=request
        )
        return Response(
            MyOrganizationSerializer(membership, context={"request": request}).data, status=status.HTTP_201_CREATED
        )


class RoleViewSet(TenantReadOnlyViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    pagination_class = None
    filter_backends = []
    required_permissions = {"list": "members.view", "retrieve": "members.view"}

    def get_base_queryset(self):
        return roles_for(self.organization)


class PermissionViewSet(TenantReadOnlyViewSet):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    pagination_class = None
    filter_backends = []
    required_permissions = {"list": "members.view"}

    def get_base_queryset(self):
        return Permission.objects.all()


class MyOrganizationsView(APIView):
    """Organization switcher data."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses=MyOrganizationSerializer(many=True))
    def get(self, request):
        return Response(
            MyOrganizationSerializer(_my_memberships(request.user), many=True, context={"request": request}).data
        )


class MyOrganizationDetailView(APIView):
    """My role, permission codes and data scopes in one organization."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request, org_id):
        context = get_org_context(request, org_id)
        membership = get_object_or_404(OrganizationMembership, pk=context.membership.pk)
        current_fy = FinancialYear.objects.for_org(context.organization).filter(is_current=True).first()
        return Response(
            {
                "organization": OrganizationSerializer(context.organization, context={"request": request}).data,
                "membership_id": str(membership.pk),
                "role": {"id": str(membership.role.pk), "code": membership.role.code, "name": membership.role.name},
                "permissions": context.permissions,
                "current_financial_year": FinancialYearSerializer(current_fy).data if current_fy else None,
                "member_portal_enabled": bool(context.organization.settings.get("member_portal_enabled")),
                "form_studio": form_studio.get_config(context.organization),
            }
        )
