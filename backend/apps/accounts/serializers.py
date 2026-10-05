from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.core.phone import normalize_mobile

from .models import Language, User


def normalize_identifier(value: str) -> tuple[str, str]:
    """Return ("email"|"mobile", normalised value)."""
    value = (value or "").strip()
    if "@" in value:
        return "email", value.lower()
    try:
        return "mobile", normalize_mobile(value)
    except DjangoValidationError as exc:
        raise serializers.ValidationError(exc.messages) from exc


class MobileField(serializers.CharField):
    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        if not value:
            return None
        try:
            return normalize_mobile(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages, code="invalid_mobile") from exc


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "full_name",
            "email",
            "mobile",
            "preferred_language",
            "email_verified_at",
            "mobile_verified_at",
            "is_platform_admin",
            "date_joined",
        ]
        read_only_fields = [f for f in fields if f not in ("full_name", "preferred_language")]


class RegisterSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    mobile = MobileField(required=False, allow_blank=True, allow_null=True)
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    preferred_language = serializers.ChoiceField(choices=Language.choices, default=Language.ENGLISH)

    def validate_email(self, value):
        return value.lower() if value else None

    def validate(self, attrs):
        if not attrs.get("email") and not attrs.get("mobile"):
            raise serializers.ValidationError(
                _("Enter an email address or a mobile number."), code="identifier_required"
            )
        candidate = User(full_name=attrs["full_name"], email=attrs.get("email"), mobile=attrs.get("mobile"))
        try:
            password_validation.validate_password(attrs["password"], candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": exc.messages}) from exc
        return attrs


class VerifySerializer(serializers.Serializer):
    destination = serializers.CharField()
    code = serializers.CharField(max_length=10)


class ResendSerializer(serializers.Serializer):
    destination = serializers.CharField()


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField(help_text="Email address or mobile number")
    password = serializers.CharField(write_only=True, style={"input_type": "password"})


class RefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField(required=False, allow_blank=True)


class ForgotPasswordSerializer(serializers.Serializer):
    identifier = serializers.CharField()


class ResetPasswordSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    code = serializers.CharField(max_length=10)
    new_password = serializers.CharField(write_only=True)


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)


def validate_new_password(password, user):
    try:
        password_validation.validate_password(password, user)
    except DjangoValidationError as exc:
        raise serializers.ValidationError({"new_password": exc.messages}) from exc


# --- Response shapes (for API documentation) ----------------------------------------------------
class TokenResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField(required=False, help_text="Omitted for web clients (sent as HttpOnly cookie)")
    user = UserSerializer()


class RefreshResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField(required=False)


class VerificationInfoSerializer(serializers.Serializer):
    destination = serializers.CharField(help_text="Masked email or mobile")
    channel = serializers.ChoiceField(choices=["email", "sms"], required=False)


class VerificationResponseSerializer(serializers.Serializer):
    verification = VerificationInfoSerializer()
    debug_code = serializers.CharField(required=False, help_text="Development only")


class DetailResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
    debug_code = serializers.CharField(required=False, help_text="Development only")
