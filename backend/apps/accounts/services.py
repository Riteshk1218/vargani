from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from apps.audit import services as audit

from .models import OTPChallenge, User
from .otp import issue_otp


class AccountExists(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("An account with these details already exists. Please log in.")
    default_code = "account_exists"


class VerificationRequired(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = _("Please verify your account before logging in.")
    default_code = "verification_required"


def find_user(kind: str, value: str) -> User | None:
    return User.objects.filter(**{kind: value}).first()


def mask(destination: str) -> str:
    if "@" in destination:
        name, domain = destination.split("@", 1)
        return f"{name[:2]}***@{domain}"
    return f"{destination[:3]}******{destination[-3:]}"


@transaction.atomic
def register_user(*, full_name, password, preferred_language, email=None, mobile=None, ip=None):
    existing = {u.pk: u for u in User.objects.filter(email=email)} if email else {}
    if mobile:
        existing.update({u.pk: u for u in User.objects.filter(mobile=mobile)})
    if len(existing) > 1 or any(u.is_verified for u in existing.values()):
        raise AccountExists()
    if existing:
        user = next(iter(existing.values()))
        user.full_name, user.email, user.mobile, user.preferred_language = full_name, email, mobile, preferred_language
        user.set_password(password)
        user.save()
    else:
        user = User.objects.create_user(
            full_name=full_name, email=email, mobile=mobile, password=password, preferred_language=preferred_language
        )
    destination = email or mobile
    code = issue_otp(destination, OTPChallenge.Purpose.REGISTER, ip=ip)
    return user, destination, code


def mark_verified(user: User, destination: str) -> None:
    now = timezone.now()
    if "@" in destination:
        user.email_verified_at = user.email_verified_at or now
    else:
        user.mobile_verified_at = user.mobile_verified_at or now
    user.save(update_fields=["email_verified_at", "mobile_verified_at"])


def verification_payload(destination: str, code: str) -> dict:
    data = {"verification": {"destination": mask(destination), "channel": "email" if "@" in destination else "sms"}}
    if settings.OTP_DEBUG_ECHO:
        data["debug_code"] = code
    return data


def is_web_client(request) -> bool:
    return request.META.get("HTTP_X_CLIENT_TYPE", "").lower() == "web"


def set_refresh_cookie(response, refresh: str) -> None:
    response.set_cookie(
        settings.REFRESH_COOKIE_NAME,
        refresh,
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        httponly=True,
        secure=settings.REFRESH_COOKIE_SECURE,
        samesite="Strict",
        path=settings.REFRESH_COOKIE_PATH,
    )


def clear_refresh_cookie(response) -> None:
    response.delete_cookie(settings.REFRESH_COOKIE_NAME, path=settings.REFRESH_COOKIE_PATH, samesite="Strict")


def token_response(request, user: User, http_status=status.HTTP_200_OK) -> Response:
    from .serializers import UserSerializer

    refresh = RefreshToken.for_user(user)
    data = {"access": str(refresh.access_token), "user": UserSerializer(user).data}
    if not is_web_client(request):
        data["refresh"] = str(refresh)
    response = Response(data, status=http_status)
    if is_web_client(request):
        set_refresh_cookie(response, str(refresh))
    user.last_login = timezone.now()
    user.save(update_fields=["last_login"])
    return response


def revoke_all_tokens(user: User) -> None:
    for token in OutstandingToken.objects.filter(user=user, expires_at__gt=timezone.now()):
        BlacklistedToken.objects.get_or_create(token=token)


def record_auth_event(request, user, action):
    audit.record(request=request, actor=user, action=action, entity_type="accounts.user", entity_id=user.pk)


def ensure_can_login(user: User | None, password: str) -> User:
    if user is None or not user.is_active or not user.check_password(password):
        raise ValidationError({"non_field_errors": [_("Invalid login details.")]}, code="invalid_credentials")
    if settings.REQUIRE_VERIFIED_LOGIN and not user.is_verified:
        raise VerificationRequired()
    return user
