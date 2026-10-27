from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.accounts.models import Language, ThemeColor
from apps.accounts.serializers import MobileField, UsernameField

from . import services
from .models import FinancialYear, Invitation, Organization, OrganizationMembership, Permission, Role

ORG_PROFILE_FIELDS = [
    "name",
    "address_line1",
    "address_line2",
    "city",
    "district",
    "state",
    "pincode",
    "country",
    "phone",
    "email",
    "website",
    "description",
    "registration_type",
    "registration_number",
    "default_language",
    "receipt_language",
    "timezone",
]


class OrganizationSerializer(serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()
    phone = MobileField(required=False, allow_blank=True)
    default_language = serializers.ChoiceField(choices=Language.choices, required=False)
    receipt_language = serializers.ChoiceField(choices=Language.choices, required=False)

    class Meta:
        model = Organization
        fields = ["id", "slug", *ORG_PROFILE_FIELDS, "currency", "logo_url", "status", "created_at", "updated_at"]
        read_only_fields = ["id", "slug", "currency", "logo_url", "status", "created_at", "updated_at"]

    def get_logo_url(self, obj) -> str | None:
        return services.logo_url(obj, self.context.get("request"))

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError(_("Enter the organization name."))
        return value

    def to_internal_value(self, data):
        values = super().to_internal_value(data)
        if values.get("phone") is None and "phone" in values:
            values["phone"] = ""
        return values


class FinancialYearInputSerializer(serializers.Serializer):
    label = serializers.CharField(max_length=20)
    start_date = serializers.DateField()
    end_date = serializers.DateField()

    def validate(self, attrs):
        if attrs["end_date"] <= attrs["start_date"]:
            raise serializers.ValidationError({"end_date": [_("End date must be after the start date.")]})
        return attrs


class OrganizationCreateSerializer(OrganizationSerializer):
    financial_year = FinancialYearInputSerializer(required=False, write_only=True)

    class Meta(OrganizationSerializer.Meta):
        fields = [*OrganizationSerializer.Meta.fields, "financial_year"]


class OrganizationSettingsSerializer(serializers.Serializer):
    allow_unassigned_collection = serializers.BooleanField(required=False)
    require_expense_approval = serializers.BooleanField(required=False)
    member_portal_enabled = serializers.BooleanField(required=False)
    auto_reminders = serializers.BooleanField(required=False)
    theme_color = serializers.ChoiceField(choices=ThemeColor.choices, required=False)


class FormStudioModeSerializer(serializers.Serializer):
    label = serializers.CharField(allow_blank=True, required=False)
    hidden = serializers.BooleanField(required=False)


class FormStudioFieldSerializer(serializers.Serializer):
    key = serializers.CharField(required=False, help_text="Empty for a new dropdown; the server assigns one.")
    label = serializers.CharField()
    options = serializers.ListField(child=serializers.CharField())
    required = serializers.BooleanField(required=False)
    active = serializers.BooleanField(required=False)


class FormStudioSerializer(serializers.Serializer):
    """Schema only: organizations/form_studio.py validates the admin studio."""

    labels = serializers.DictField(child=serializers.CharField(allow_blank=True), required=False)
    modes = serializers.DictField(child=FormStudioModeSerializer(), required=False)
    custom_fields = FormStudioFieldSerializer(many=True, required=False)


class LogoUploadSerializer(serializers.Serializer):
    logo = serializers.FileField()


class FinancialYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialYear
        fields = ["id", "label", "start_date", "end_date", "status", "is_current", "created_at", "updated_at"]
        read_only_fields = ["id", "status", "is_current", "created_at", "updated_at"]

    def validate(self, attrs):
        org = self.context["organization"]
        instance = self.instance
        start = attrs.get("start_date", instance.start_date if instance else None)
        end = attrs.get("end_date", instance.end_date if instance else None)
        label = attrs.get("label", instance.label if instance else None)
        if instance and instance.status == FinancialYear.Status.CLOSED:
            raise serializers.ValidationError(_("A closed financial year cannot be edited."))
        if start and end and end <= start:
            raise serializers.ValidationError({"end_date": [_("End date must be after the start date.")]})
        others = FinancialYear.objects.filter(organization=org)
        if instance:
            others = others.exclude(pk=instance.pk)
        if others.filter(label=label).exists():
            raise serializers.ValidationError({"label": [_("A financial year with this label already exists.")]})
        if others.filter(start_date__lte=end, end_date__gte=start).exists():
            raise serializers.ValidationError(_("This financial year overlaps another financial year."))
        return attrs


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ["code", "module", "description"]


class RoleSerializer(serializers.ModelSerializer):
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = ["id", "code", "name", "description", "is_system", "permissions"]

    def get_permissions(self, obj) -> dict[str, str]:
        return {rp.permission.code: rp.scope for rp in obj.role_permissions.all()}


class RoleSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ["id", "code", "name"]


class MemberSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    role = RoleSummarySerializer(read_only=True)
    role_id = serializers.PrimaryKeyRelatedField(
        source="role", queryset=Role.objects.none(), write_only=True, required=False
    )

    class Meta:
        model = OrganizationMembership
        fields = ["id", "user", "role", "role_id", "status", "can_download", "can_reset_password", "joined_at"]
        read_only_fields = ["id", "user", "role", "can_reset_password", "joined_at"]

    can_reset_password = serializers.SerializerMethodField()

    def get_can_reset_password(self, obj) -> bool:
        return services.can_admin_reset_password(obj)

    def get_fields(self):
        fields = super().get_fields()
        org = self.context.get("organization")
        if org is not None:
            fields["role_id"].queryset = services.assignable_roles(org)
        return fields

    def get_user(self, obj) -> dict[str, str | None]:
        return {
            "id": str(obj.user.pk),
            "full_name": obj.user.full_name,
            "username": obj.user.username,
            "email": obj.user.email,
            "mobile": obj.user.mobile,
        }


class InvitationSerializer(serializers.ModelSerializer):
    role = RoleSummarySerializer(read_only=True)
    role_id = serializers.PrimaryKeyRelatedField(source="role", queryset=Role.objects.none(), write_only=True)
    mobile = MobileField(required=False, allow_blank=True, allow_null=True)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = Invitation
        fields = ["id", "full_name", "email", "mobile", "role", "role_id", "status", "expires_at", "created_at"]
        read_only_fields = ["id", "role", "status", "expires_at", "created_at"]

    def get_fields(self):
        fields = super().get_fields()
        org = self.context.get("organization")
        if org is not None:
            fields["role_id"].queryset = services.assignable_roles(org)
        return fields

    def validate(self, attrs):
        attrs["email"] = (attrs.get("email") or "").lower() or None
        attrs["mobile"] = attrs.get("mobile") or None
        if not attrs["email"] and not attrs["mobile"]:
            raise serializers.ValidationError(_("Enter an email address or a mobile number."))
        return attrs


def _check_password(password, *, full_name="", email=None, mobile=None, username=None):
    from django.contrib.auth import password_validation
    from django.core.exceptions import ValidationError as DjangoValidationError

    from apps.accounts.models import User

    try:
        password_validation.validate_password(
            password, User(full_name=full_name, email=email, mobile=mobile, username=username)
        )
    except DjangoValidationError as exc:
        raise serializers.ValidationError({"password": exc.messages}) from exc


class LoginDetailsSerializer(serializers.Serializer):
    """Name, a username, email or mobile, and a password that an admin types in for someone else."""

    full_name = serializers.CharField(max_length=150)
    username = UsernameField(required=False, allow_blank=True, allow_null=True)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    mobile = MobileField(required=False, allow_blank=True, allow_null=True)
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate_full_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError(_("Enter the name."))
        return value

    def validate(self, attrs):
        attrs["email"] = (attrs.get("email") or "").lower() or None
        attrs["mobile"] = attrs.get("mobile") or None
        attrs["username"] = attrs.get("username") or None
        if not attrs["email"] and not attrs["mobile"] and not attrs["username"]:
            raise serializers.ValidationError(_("Enter a username, an email address or a mobile number."))
        _check_password(
            attrs["password"],
            full_name=attrs["full_name"],
            email=attrs["email"],
            mobile=attrs["mobile"],
            username=attrs["username"],
        )
        return attrs


class MemberCreateSerializer(LoginDetailsSerializer):
    role_id = serializers.PrimaryKeyRelatedField(source="role", queryset=Role.objects.none())

    def get_fields(self):
        fields = super().get_fields()
        org = self.context.get("organization")
        if org is not None:
            fields["role_id"].queryset = services.assignable_roles(org)
        return fields


class SetPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate_password(self, value):
        user = self.context.get("user")
        _check_password(
            value,
            full_name=getattr(user, "full_name", ""),
            email=getattr(user, "email", None),
            username=getattr(user, "username", None),
        )
        return value


class InvitationAcceptSerializer(serializers.Serializer):
    token = serializers.CharField()


class MyOrganizationSerializer(serializers.Serializer):
    """One row of the organization switcher."""

    id = serializers.UUIDField(source="organization.id")
    name = serializers.CharField(source="organization.name")
    logo_url = serializers.SerializerMethodField()
    role = RoleSummarySerializer()
    membership_id = serializers.UUIDField(source="id")

    def get_logo_url(self, obj) -> str | None:
        return services.logo_url(obj.organization, self.context.get("request"))


def roles_for(org):
    return Role.objects.filter(Q(organization__isnull=True) | Q(organization=org)).prefetch_related(
        "role_permissions__permission"
    )
