"""The platform owner's view across every organization (the Platform Admin).

The owner sees which organizations use Vargani, who their admins and users are and how big they are, and
can start a new organization with its admin login, suspend or reactivate one, and help a user who is locked
out. Money, people's details, receipts and expenses stay private to each organization: the owner sees counts
only. To work inside an organization the owner must be given a role in it like anyone else.
"""

from django.db import transaction
from django.db.models import Count, OuterRef, Prefetch, Q, Subquery, Value
from django.db.models.functions import Coalesce
from django.forms.models import model_to_dict
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.audit import services as audit
from apps.core.exceptions import BusinessRuleViolation

from . import services
from .catalog import ADMIN_ROLE
from .models import Organization, OrganizationMembership
from .serializers import FinancialYearInputSerializer, LoginDetailsSerializer, SetPasswordSerializer


class IsPlatformAdmin(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_active and user.is_platform_admin)


class PlatformView:
    permission_classes = [IsAuthenticated, IsPlatformAdmin]


def _count(model, **filters):
    rows = model.objects.filter(organization=OuterRef("pk"), **filters).order_by().values("organization")
    return Coalesce(Subquery(rows.annotate(n=Count("pk")).values("n")[:1]), Value(0))


def _organizations():
    from apps.events.models import Event
    from apps.people.models import Person
    from apps.receipts.models import Receipt

    admins = OrganizationMembership.objects.filter(
        role__code=ADMIN_ROLE, status=OrganizationMembership.Status.ACTIVE
    ).select_related("user")
    return Organization.objects.annotate(
        users_count=_count(OrganizationMembership, status=OrganizationMembership.Status.ACTIVE),
        people_count=_count(Person, deleted_at__isnull=True),
        events_count=_count(Event, deleted_at__isnull=True),
        receipts_count=_count(Receipt),
    ).prefetch_related(Prefetch("memberships", queryset=admins, to_attr="admin_memberships"))


class PlatformOrganizationSerializer(serializers.ModelSerializer):
    users_count = serializers.IntegerField(read_only=True)
    people_count = serializers.IntegerField(read_only=True)
    events_count = serializers.IntegerField(read_only=True)
    receipts_count = serializers.IntegerField(read_only=True)
    admins = serializers.SerializerMethodField()
    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = [
            "id",
            "name",
            "city",
            "state",
            "phone",
            "email",
            "status",
            "logo_url",
            "created_at",
            "users_count",
            "people_count",
            "events_count",
            "receipts_count",
            "admins",
        ]

    def get_admins(self, obj) -> list[dict]:
        return [
            {"id": str(m.user.pk), "full_name": m.user.full_name, "email": m.user.email, "mobile": m.user.mobile}
            for m in getattr(obj, "admin_memberships", [])
        ]

    def get_logo_url(self, obj) -> str | None:
        return services.logo_url(obj, self.context.get("request"))


class PlatformOrganizationCreateSerializer(LoginDetailsSerializer):
    """The organization's name, plus full_name, email or mobile and password of its first admin."""

    name = serializers.CharField(max_length=200)
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    financial_year = FinancialYearInputSerializer(required=False)

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError(_("Enter the organization name."))
        return value


class PlatformUserSerializer(serializers.ModelSerializer):
    organizations = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "full_name",
            "email",
            "mobile",
            "is_active",
            "is_platform_admin",
            "last_login",
            "date_joined",
            "organizations",
        ]

    def get_organizations(self, obj) -> list[dict]:
        return [
            {
                "id": str(m.organization.pk),
                "name": m.organization.name,
                "role": {"code": m.role.code, "name": m.role.name},
                "status": m.status,
            }
            for m in obj.memberships.all()
        ]


class PlatformSummaryView(PlatformView, APIView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        from apps.people.models import Person
        from apps.receipts.models import Receipt

        orgs = Organization.objects.aggregate(
            total=Count("pk"),
            active=Count("pk", filter=Q(status=Organization.Status.ACTIVE)),
            suspended=Count("pk", filter=Q(status=Organization.Status.SUSPENDED)),
        )
        return Response(
            {
                "organizations": orgs,
                "users": User.objects.count(),
                "people": Person.objects.filter(deleted_at__isnull=True).count(),
                "receipts": Receipt.objects.count(),
            }
        )


class PlatformOrganizationListView(PlatformView, ListAPIView):
    serializer_class = PlatformOrganizationSerializer
    search_fields = ["name", "city", "memberships__user__full_name", "memberships__user__email"]
    filterset_fields = ["status"]

    def get_queryset(self):
        return _organizations().order_by("-created_at")

    def filter_queryset(self, queryset):
        return super().filter_queryset(queryset).distinct()

    @extend_schema(request=PlatformOrganizationCreateSerializer, responses=PlatformOrganizationSerializer)
    def post(self, request):
        """Start a new organization for a customer, with its first Organization Admin login."""
        serializer = PlatformOrganizationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        with transaction.atomic():
            user, created = services.create_login(
                full_name=data["full_name"], email=data["email"], mobile=data["mobile"], password=data["password"]
            )
            org = services.create_organization(
                user=user,
                request=request,
                financial_year=data.get("financial_year"),
                name=data["name"],
                city=data.get("city", ""),
            )
            audit.record(
                request=request,
                actor=request.user,
                organization=org,
                action=audit.CREATE,
                entity_type="organizations.organization",
                entity_id=org.pk,
                after={"reason": "created_by_platform_admin", "admin": str(user.pk), "new_login": created},
            )
        body = PlatformOrganizationSerializer(_organizations().get(pk=org.pk), context={"request": request}).data
        body["new_login"] = created
        return Response(body, status=status.HTTP_201_CREATED)


class PlatformOrganizationStatusView(PlatformView, APIView):
    class InputSerializer(serializers.Serializer):
        status = serializers.ChoiceField(choices=[Organization.Status.ACTIVE, Organization.Status.SUSPENDED])

    @extend_schema(request=InputSerializer, responses=PlatformOrganizationSerializer)
    def post(self, request, org_id):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            org = get_object_or_404(Organization.objects.select_for_update(), pk=org_id)
            if org.status == Organization.Status.CLOSED:
                raise BusinessRuleViolation(_("A closed organization cannot be changed."))
            before = {"status": org.status}
            org.status = serializer.validated_data["status"]
            org.save(update_fields=["status", "updated_at"])
            audit.record(
                request=request,
                organization=org,
                action=audit.STATUS_CHANGE,
                entity_type="organizations.organization",
                entity_id=org.pk,
                before=before,
                after={"status": org.status, "reason": "platform_admin"},
            )
        fresh = _organizations().get(pk=org.pk)
        return Response(PlatformOrganizationSerializer(fresh, context={"request": request}).data)


class PlatformUserListView(PlatformView, ListAPIView):
    serializer_class = PlatformUserSerializer
    search_fields = ["full_name", "email", "mobile", "memberships__organization__name"]
    filterset_fields = ["is_active"]

    def get_queryset(self):
        memberships = OrganizationMembership.objects.select_related("organization", "role").order_by(
            "organization__name"
        )
        return User.objects.prefetch_related(Prefetch("memberships", queryset=memberships)).order_by("-date_joined")

    def filter_queryset(self, queryset):
        return super().filter_queryset(queryset).distinct()


def _platform_user(request, user_id) -> User:
    user = get_object_or_404(User, pk=user_id)
    if user.pk == request.user.pk:
        raise BusinessRuleViolation(_("Change your own password and details from My profile."))
    return user


class PlatformUserPasswordView(PlatformView, APIView):
    """Support: set a new password for a user who is locked out. They are logged out everywhere."""

    @extend_schema(request=SetPasswordSerializer, responses=OpenApiTypes.OBJECT)
    def post(self, request, user_id):
        from apps.accounts.services import revoke_all_tokens

        user = _platform_user(request, user_id)
        serializer = SetPasswordSerializer(data=request.data, context={"user": user})
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            user.set_password(serializer.validated_data["password"])
            user.save(update_fields=["password"])
            revoke_all_tokens(user)
            audit.record(
                request=request,
                action=audit.PASSWORD_CHANGE,
                entity_type="accounts.user",
                entity_id=user.pk,
                after={"reason": "set_by_platform_admin"},
            )
        return Response({"detail": "ok"})


class PlatformUserStatusView(PlatformView, APIView):
    """Block or unblock a login on the whole platform."""

    class InputSerializer(serializers.Serializer):
        is_active = serializers.BooleanField()

    @extend_schema(request=InputSerializer, responses=PlatformUserSerializer)
    def post(self, request, user_id):
        from apps.accounts.services import revoke_all_tokens

        user = _platform_user(request, user_id)
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            before = model_to_dict(user, fields=["is_active"])
            user.is_active = serializer.validated_data["is_active"]
            user.save(update_fields=["is_active"])
            if not user.is_active:
                revoke_all_tokens(user)
            audit.record(
                request=request,
                action=audit.STATUS_CHANGE,
                entity_type="accounts.user",
                entity_id=user.pk,
                before=before,
                after={"is_active": user.is_active, "reason": "platform_admin"},
            )
        return Response(PlatformUserSerializer(self._fresh(user)).data)

    @staticmethod
    def _fresh(user):
        return PlatformUserListView().get_queryset().get(pk=user.pk)
