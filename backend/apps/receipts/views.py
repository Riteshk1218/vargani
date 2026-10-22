import django_filters
from django.http import HttpResponse
from django.utils.translation import gettext_noop
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.core.downloads import Col, ListDownloadMixin
from apps.core.scoping import scope_money
from apps.core.tenancy import SCOPE_ALL
from apps.core.viewsets import TenantReadOnlyViewSet
from apps.organizations.services import logo_url

from . import rendering, voids
from .models import Receipt, ReceiptVoidRequest
from .serializers import ReceiptSerializer, ReceiptVoidRequestSerializer


class ReceiptFilter(django_filters.FilterSet):
    date_from = django_filters.DateFilter(field_name="issued_at", lookup_expr="date__gte")
    date_to = django_filters.DateFilter(field_name="issued_at", lookup_expr="date__lte")

    class Meta:
        model = Receipt
        fields = ["event", "status", "payment"]


class ReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=300, required=False, allow_blank=True, default="")


class ShareSerializer(serializers.Serializer):
    share_url = serializers.URLField()
    expires_at = serializers.DateTimeField()
    whatsapp_text = serializers.CharField()
    whatsapp_url = serializers.URLField()


def pdf_response(receipt, inline=False):
    response = HttpResponse(rendering.receipt_pdf(receipt), content_type="application/pdf")
    disposition = "inline" if inline else "attachment"
    response["Content-Disposition"] = f'{disposition}; filename="{receipt.receipt_number}.pdf"'
    response["Cache-Control"] = "private, no-store"
    return response


class ReceiptViewSet(ListDownloadMixin, TenantReadOnlyViewSet):
    """Issued receipts. Receipts are created only by recording a successful payment and never edited.

    A receipt is corrected by requesting a void (approved by someone with receipts.void_approve) and then
    recording the right payment with `replaces_receipt`.
    """

    queryset = Receipt.objects.all()
    download_title = gettext_noop("Receipt register")
    download_columns = [
        Col("receipt_number", gettext_noop("Receipt no.")),
        Col("issued_at", gettext_noop("Date"), "datetime"),
        Col("payer_name", gettext_noop("Name")),
        Col("mode", gettext_noop("Payment mode"), "mode"),
        Col("status", gettext_noop("Status"), "status"),
        Col("void_reason", gettext_noop("Void reason")),
        Col("amount", gettext_noop("Amount"), "money"),
    ]
    serializer_class = ReceiptSerializer
    filterset_class = ReceiptFilter
    search_fields = ["receipt_number", "payment__payer__full_name", "payment__payer__mobile"]
    ordering_fields = ["issued_at", "sequence"]
    http_method_names = ["get", "post", "head", "options"]
    required_permissions = {
        "list": "receipts.view",
        "retrieve": "receipts.view",
        "pdf": "receipts.view",
        "share": "receipts.share",
        "void_request": "receipts.void_request",
    }

    def get_base_queryset(self):
        return Receipt.objects.for_org(self.organization).select_related("payment__payer", "replaces_receipt")

    def scope_queryset(self, queryset):
        return scope_money(
            queryset,
            self.org_context,
            "receipts.view",
            self.request.user,
            collector="payment__collector",
            person="payment__payer",
        )

    @extend_schema(responses={(200, "application/pdf"): OpenApiTypes.BINARY})
    @action(detail=True, methods=["get"])
    def pdf(self, request, pk=None):
        return pdf_response(self.get_object(), inline=request.query_params.get("inline") == "1")

    @extend_schema(request=None, responses=ShareSerializer)
    @action(detail=True, methods=["post"])
    def share(self, request, pk=None):
        receipt = self.get_object()
        if self.org_context.scope("receipts.share") != SCOPE_ALL and receipt.payment.collector_id != self.membership.pk:
            raise PermissionDenied()
        return Response(ShareSerializer(rendering.create_share(receipt, request=request, actor=request.user)).data)

    @extend_schema(request=ReasonSerializer, responses={201: ReceiptVoidRequestSerializer})
    @action(detail=True, methods=["post"], url_path="void-request")
    def void_request(self, request, pk=None):
        receipt = self.get_object()
        if (
            self.org_context.scope("receipts.void_request") != SCOPE_ALL
            and receipt.payment.collector_id != self.membership.pk
        ):
            raise PermissionDenied()
        serializer = ReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        void_request = voids.request_void(
            receipt, reason=serializer.validated_data["reason"], request=request, actor=request.user
        )
        return Response(ReceiptVoidRequestSerializer(void_request).data, status=201)


class ReceiptVoidRequestViewSet(TenantReadOnlyViewSet):
    """Void requests. Approvers see all; requesters see their own."""

    queryset = ReceiptVoidRequest.objects.all()
    serializer_class = ReceiptVoidRequestSerializer
    filterset_fields = ["status", "receipt"]
    ordering_fields = ["created_at"]
    http_method_names = ["get", "post", "head", "options"]
    required_permissions = {
        "list": ("receipts.void_approve", "receipts.void_request"),
        "retrieve": ("receipts.void_approve", "receipts.void_request"),
        "approve": "receipts.void_approve",
        "reject": "receipts.void_approve",
    }

    def get_base_queryset(self):
        return ReceiptVoidRequest.objects.for_org(self.organization).select_related(
            "receipt__payment__payer", "requested_by", "decided_by"
        )

    def scope_queryset(self, queryset):
        if self.org_context.has("receipts.void_approve"):
            return queryset
        return queryset.filter(requested_by=self.request.user)

    @extend_schema(request=ReasonSerializer, responses=ReceiptVoidRequestSerializer)
    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        serializer = ReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = voids.approve(
            self.get_object(),
            approver_membership=self.membership,
            note=serializer.validated_data["reason"],
            request=request,
            actor=request.user,
        )
        return Response(ReceiptVoidRequestSerializer(self.get_base_queryset().get(pk=result.pk)).data)

    @extend_schema(request=ReasonSerializer, responses=ReceiptVoidRequestSerializer)
    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        serializer = ReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = voids.reject(
            self.get_object(), note=serializer.validated_data["reason"], request=request, actor=request.user
        )
        return Response(ReceiptVoidRequestSerializer(self.get_base_queryset().get(pk=result.pk)).data)


class PublicReceiptView(APIView):
    """What a contributor sees from a WhatsApp link. No login; the token is the only key and expires."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "public_receipt"

    def _share(self, token):
        share = rendering.find_share(token)
        if share is None:
            raise NotFound()
        return share

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request, token):
        receipt = self._share(token).receipt
        s = receipt.snapshot
        return Response(
            {
                "receipt_number": receipt.receipt_number,
                "status": receipt.status,
                "issued_at": receipt.issued_at,
                "language": receipt.language,
                "snapshot": {k: v for k, v in s.items() if k != "collector"},
                "logo_url": logo_url(receipt.organization, request) if s["organization"].get("logo") else None,
            }
        )


class PublicReceiptPdfView(PublicReceiptView):
    @extend_schema(responses={(200, "application/pdf"): OpenApiTypes.BINARY})
    def get(self, request, token):
        return pdf_response(self._share(token).receipt)
