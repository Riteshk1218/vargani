from django.conf import settings
from django.utils.translation import gettext as _
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from apps.audit import services as audit
from apps.audit.services import _client_ip

from . import services
from .models import OTPChallenge
from .otp import issue_otp, verify_otp
from .serializers import (
    ChangePasswordSerializer,
    DetailResponseSerializer,
    ForgotPasswordSerializer,
    LoginSerializer,
    RefreshResponseSerializer,
    RefreshSerializer,
    RegisterSerializer,
    ResendSerializer,
    ResetPasswordSerializer,
    TokenResponseSerializer,
    UserSerializer,
    VerificationResponseSerializer,
    VerifySerializer,
    normalize_identifier,
    validate_new_password,
)
from .throttles import AuthThrottle, OTPThrottle


class PublicAuthView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [AuthThrottle]

    def get_authenticate_header(self, request):
        # Keep 401 (not 403) for invalid/expired tokens even though these views skip authentication.
        return 'Bearer realm="api"'


class RegisterView(PublicAuthView):
    throttle_classes = [OTPThrottle]

    @extend_schema(request=RegisterSerializer, responses={201: VerificationResponseSerializer})
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user, destination, code = services.register_user(**serializer.validated_data, ip=_client_ip(request))
        return Response(services.verification_payload(destination, code), status=status.HTTP_201_CREATED)


class VerifyView(PublicAuthView):
    @extend_schema(request=VerifySerializer, responses=TokenResponseSerializer)
    def post(self, request):
        serializer = VerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        kind, destination = normalize_identifier(serializer.validated_data["destination"])
        verify_otp(destination, OTPChallenge.Purpose.REGISTER, serializer.validated_data["code"])
        user = services.find_user(kind, destination)
        if user is None or not user.is_active:
            raise ValidationError({"code": [_("The code is invalid or has expired.")]})
        services.mark_verified(user, destination)
        services.record_auth_event(request, user, "verify")
        return services.token_response(request, user)


class ResendVerificationView(PublicAuthView):
    throttle_classes = [OTPThrottle]

    @extend_schema(request=ResendSerializer, responses=VerificationResponseSerializer)
    def post(self, request):
        serializer = ResendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        kind, destination = normalize_identifier(serializer.validated_data["destination"])
        user = services.find_user(kind, destination)
        payload = {"verification": {"destination": services.mask(destination)}}
        if user is not None and not user.is_verified:
            code = issue_otp(destination, OTPChallenge.Purpose.REGISTER, ip=_client_ip(request))
            payload = services.verification_payload(destination, code)
        return Response(payload)  # same response whether or not the account exists


class LoginView(PublicAuthView):
    @extend_schema(request=LoginSerializer, responses=TokenResponseSerializer)
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        kind, value = normalize_identifier(serializer.validated_data["identifier"])
        user = services.find_user(kind, value)
        try:
            services.ensure_can_login(user, serializer.validated_data["password"])
        except ValidationError:
            if user is not None:
                services.record_auth_event(request, user, audit.LOGIN_FAILED)
            raise
        services.record_auth_event(request, user, audit.LOGIN)
        return services.token_response(request, user)


class RefreshView(PublicAuthView):
    throttle_classes = []

    @extend_schema(request=RefreshSerializer, responses=RefreshResponseSerializer)
    def post(self, request):
        token = request.data.get("refresh") or request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
        from_cookie = not request.data.get("refresh") and bool(token)
        if from_cookie and not services.is_web_client(request):
            # Cookie-based refresh requires the custom header, which cross-site forms cannot send.
            raise ValidationError({"refresh": [_("Refresh token required.")]})
        if not token:
            raise ValidationError({"refresh": [_("Refresh token required.")]})
        serializer = TokenRefreshSerializer(data={"refresh": token})
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as exc:
            from rest_framework_simplejwt.exceptions import InvalidToken

            raise InvalidToken(exc.args[0]) from exc
        data = dict(serializer.validated_data)
        response = Response({"access": data["access"]})
        if services.is_web_client(request):
            services.set_refresh_cookie(response, data.get("refresh", token))
        else:
            response.data["refresh"] = data.get("refresh", token)
        return response


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=RefreshSerializer, responses={204: None})
    def post(self, request):
        token = request.data.get("refresh") or request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
        if token:
            try:
                refresh = RefreshToken(token)
                if str(refresh.get("user_id")) == str(request.user.pk):
                    refresh.blacklist()
            except TokenError:
                pass
        services.record_auth_event(request, request.user, audit.LOGOUT)
        response = Response(status=status.HTTP_204_NO_CONTENT)
        services.clear_refresh_cookie(response)
        return response


class ForgotPasswordView(PublicAuthView):
    throttle_classes = [OTPThrottle]

    @extend_schema(request=ForgotPasswordSerializer, responses=DetailResponseSerializer)
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        kind, value = normalize_identifier(serializer.validated_data["identifier"])
        user = services.find_user(kind, value)
        payload = {"detail": _("If an account exists, a reset code has been sent.")}
        if user is not None and user.is_active:
            code = issue_otp(value, OTPChallenge.Purpose.RESET, ip=_client_ip(request))
            if settings.OTP_DEBUG_ECHO:
                payload["debug_code"] = code
        return Response(payload)


class ResetPasswordView(PublicAuthView):
    @extend_schema(request=ResetPasswordSerializer, responses=DetailResponseSerializer)
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        kind, value = normalize_identifier(serializer.validated_data["identifier"])
        verify_otp(value, OTPChallenge.Purpose.RESET, serializer.validated_data["code"])
        user = services.find_user(kind, value)
        if user is None or not user.is_active:
            raise ValidationError({"code": [_("The code is invalid or has expired.")]})
        validate_new_password(serializer.validated_data["new_password"], user)
        user.set_password(serializer.validated_data["new_password"])
        services.mark_verified(user, value)  # receiving the code proves control of this identifier
        user.save()
        services.revoke_all_tokens(user)
        services.record_auth_event(request, user, audit.PASSWORD_CHANGE)
        return Response({"detail": _("Your password has been reset. Please log in.")})


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=ChangePasswordSerializer, responses=TokenResponseSerializer)
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(serializer.validated_data["current_password"]):
            raise ValidationError({"current_password": [_("Your current password is incorrect.")]})
        validate_new_password(serializer.validated_data["new_password"], user)
        user.set_password(serializer.validated_data["new_password"])
        user.save()
        services.revoke_all_tokens(user)
        services.record_auth_event(request, user, audit.PASSWORD_CHANGE)
        return services.token_response(request, user)


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        return self.request.user
