"""Member login with a mobile number and a one-time code (no password)."""

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.translation import gettext as _
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.accounts import services as accounts
from apps.accounts.models import OTPChallenge
from apps.accounts.otp import issue_otp, verify_otp
from apps.accounts.serializers import MobileField, TokenResponseSerializer, VerificationResponseSerializer
from apps.accounts.throttles import OTPThrottle
from apps.accounts.views import PublicAuthView
from apps.audit.services import _client_ip

from .linking import auto_link, eligible_people


class MobileSerializer(serializers.Serializer):
    mobile = MobileField()


class MobileCodeSerializer(serializers.Serializer):
    mobile = MobileField()
    code = serializers.CharField(max_length=10)


def _can_use_otp_login(mobile) -> bool:
    user = get_user_model().objects.filter(mobile=mobile).first()
    if user is not None:
        return user.is_active
    return eligible_people(mobile).exists()


class MemberOTPRequestView(PublicAuthView):
    """Send a login code by SMS. The response is the same whether or not the number is known."""

    throttle_classes = [OTPThrottle]

    @extend_schema(request=MobileSerializer, responses=VerificationResponseSerializer)
    def post(self, request):
        serializer = MobileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        mobile = serializer.validated_data["mobile"]
        if not mobile:
            raise ValidationError({"mobile": [_("Enter your mobile number.")]})
        payload = {"verification": {"destination": accounts.mask(mobile), "channel": "sms"}}
        if _can_use_otp_login(mobile):
            code = issue_otp(mobile, OTPChallenge.Purpose.LOGIN, ip=_client_ip(request))
            payload = accounts.verification_payload(mobile, code)
        return Response(payload)


class MemberOTPVerifyView(PublicAuthView):
    """Check the code and log in. A first-time member gets an account and is linked to their record when
    exactly one person in an organization with the member portal has this number."""

    @extend_schema(request=MobileCodeSerializer, responses=TokenResponseSerializer)
    def post(self, request):
        serializer = MobileCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        mobile = serializer.validated_data["mobile"]
        verify_otp(mobile, OTPChallenge.Purpose.LOGIN, serializer.validated_data["code"])
        with transaction.atomic():
            User = get_user_model()
            user = User.objects.select_for_update().filter(mobile=mobile).first()
            if user is None:
                names = {p.full_name for p in eligible_people(mobile)}
                if not names:
                    raise ValidationError({"code": [_("The code is invalid or has expired.")]})
                user = User.objects.create_user(
                    full_name=names.pop() if len(names) == 1 else _("Member"), mobile=mobile
                )
            if not user.is_active:
                raise ValidationError({"code": [_("The code is invalid or has expired.")]})
            accounts.mark_verified(user, mobile)
            auto_link(user, request=request)
        accounts.record_auth_event(request, user, "login")
        return accounts.token_response(request, user)
