import json

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit import services as audit
from apps.core.fields import TenantPrimaryKeyRelatedField
from apps.core.permissions import HasOrgPermission
from apps.events.models import Event
from apps.organizations.models import Organization
from apps.payments.serializers import PaymentLineInputSerializer, PaymentSerializer
from apps.payments.services import LineInput
from apps.portal.views import PortalMixin

from . import crypto, services
from .models import GatewayConfig


class GatewayConfigSerializer(serializers.ModelSerializer):
    key_secret = serializers.CharField(write_only=True, required=False, allow_blank=True)
    webhook_secret = serializers.CharField(write_only=True, required=False, allow_blank=True)
    has_key_secret = serializers.SerializerMethodField()
    has_webhook_secret = serializers.SerializerMethodField()
    webhook_url = serializers.SerializerMethodField()

    class Meta:
        model = GatewayConfig
        fields = [
            "provider",
            "key_id",
            "key_secret",
            "webhook_secret",
            "is_active",
            "has_key_secret",
            "has_webhook_secret",
            "webhook_url",
        ]

    def get_has_key_secret(self, obj) -> bool:
        return bool(obj.key_secret_encrypted)

    def get_has_webhook_secret(self, obj) -> bool:
        return bool(obj.webhook_secret_encrypted)

    def get_webhook_url(self, obj) -> str:
        return f"{settings.API_PUBLIC_URL}/api/v1/webhooks/{obj.provider}/{obj.organization_id}/"

    def validate(self, attrs):
        secret = attrs.get("key_secret") or (self.instance and self.instance.key_secret_encrypted)
        if (
            attrs.get("is_active")
            and not (attrs.get("key_id") or getattr(self.instance, "key_id", ""))
            or (attrs.get("is_active") and not secret)
        ):
            raise serializers.ValidationError({"is_active": ["Add the key id and key secret before switching on."]})
        return attrs


class GatewayConfigView(APIView):
    """The organization's payment gateway keys. Secrets are write-only and stored encrypted."""

    permission_classes = [IsAuthenticated, HasOrgPermission]

    def get_organization_id(self):
        return None

    def get_required_permissions(self):
        return "organization.manage"

    @extend_schema(responses=GatewayConfigSerializer)
    def get(self, request):
        org = request._org_context.organization
        config = GatewayConfig.objects.filter(organization=org).first() or GatewayConfig(organization=org)
        return Response(GatewayConfigSerializer(config).data)

    @extend_schema(request=GatewayConfigSerializer, responses=GatewayConfigSerializer)
    def put(self, request):
        org = request._org_context.organization
        config = GatewayConfig.objects.filter(organization=org).first()
        serializer = GatewayConfigSerializer(config, data=request.data, partial=config is not None)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        key_secret, webhook_secret = data.pop("key_secret", None), data.pop("webhook_secret", None)
        config = config or GatewayConfig(organization=org, created_by=request.user)
        for field, value in data.items():
            setattr(config, field, value)
        if key_secret:
            config.key_secret_encrypted = crypto.encrypt(key_secret)
        if webhook_secret:
            config.webhook_secret_encrypted = crypto.encrypt(webhook_secret)
        config.updated_by = request.user
        config.save()
        audit.record(
            request=request,
            organization=org,
            action=audit.UPDATE,
            entity_type="gateway.gatewayconfig",
            entity_id=config.pk,
            after={
                "provider": config.provider,
                "key_id": config.key_id,
                "is_active": config.is_active,
                "key_secret_changed": bool(key_secret),
                "webhook_secret_changed": bool(webhook_secret),
            },
        )
        return Response(GatewayConfigSerializer(config).data)


class PortalPayRequestSerializer(serializers.Serializer):
    event = TenantPrimaryKeyRelatedField(queryset=Event.objects.filter(deleted_at__isnull=True))
    lines = PaymentLineInputSerializer(many=True, allow_empty=False, max_length=12)


class PortalPayVerifySerializer(serializers.Serializer):
    order_id = serializers.CharField(max_length=100)
    payment_id = serializers.CharField(max_length=100)
    signature = serializers.CharField(max_length=200)


class PortalPayView(PortalMixin, APIView):
    """Start an online payment for myself. Returns the gateway checkout options."""

    @extend_schema(request=PortalPayRequestSerializer, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        person = self.person()
        body = PortalPayRequestSerializer(data=request.data, context={"request": request})
        body.is_valid(raise_exception=True)
        payment, checkout = services.start(
            org=self.org,
            event=body.validated_data["event"],
            payer=person,
            lines=[LineInput(**line) for line in body.validated_data["lines"]],
            request=request,
            actor=request.user,
        )
        return Response({"payment": str(payment.pk), "checkout": checkout}, status=status.HTTP_201_CREATED)


class PortalPayVerifyView(PortalMixin, APIView):
    """Called by the website or app after checkout; the receipt is issued once the signature checks out."""

    @extend_schema(request=PortalPayVerifySerializer, responses=PaymentSerializer)
    def post(self, request):
        person = self.person()
        body = PortalPayVerifySerializer(data=request.data)
        body.is_valid(raise_exception=True)
        payment = services.confirm_checkout(org=self.org, actor=request.user, **body.validated_data)
        if payment.payer_id != person.pk:
            return Response(status=status.HTTP_404_NOT_FOUND)
        payment.refresh_from_db()
        return Response(PaymentSerializer(payment, context={"request": request}).data)


@csrf_exempt
def razorpay_webhook(request, org_id):
    """Public endpoint for Razorpay. Authenticated by the HMAC signature only; always answers quickly."""
    if request.method != "POST":
        return HttpResponse(status=405)
    org = Organization.objects.filter(pk=org_id).first()
    if org is None:
        return HttpResponse(status=404)
    body = request.body
    try:
        payload = json.loads(body or b"{}")
    except ValueError:
        return HttpResponse(status=400)
    result = services.handle_webhook(
        org=org,
        body=body,
        signature=request.headers.get("X-Razorpay-Signature", ""),
        event_id=request.headers.get("X-Razorpay-Event-Id", ""),
        payload=payload,
    )
    return HttpResponse(result, status=400 if result == "rejected" else 200, content_type="text/plain")
