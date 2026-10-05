import django_filters
from django.utils.translation import gettext as _
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.core.scoping import scope_money
from apps.core.tenancy import SCOPE_ALL
from apps.core.viewsets import TenantModelViewSet

from . import services
from .models import Payment
from .serializers import (
    PaymentCreateSerializer,
    PaymentNotesSerializer,
    PaymentSerializer,
    PaymentStatusChangeSerializer,
)


class PaymentFilter(django_filters.FilterSet):
    date_from = django_filters.DateFilter(field_name="paid_at", lookup_expr="date__gte")
    date_to = django_filters.DateFilter(field_name="paid_at", lookup_expr="date__lte")

    class Meta:
        model = Payment
        fields = ["event", "status", "mode", "payer", "collector"]


class PaymentViewSet(TenantModelViewSet):
    """Payments with their contribution lines and receipt.

    POST records a payment (also exposed as POST /collections/). Send an `Idempotency-Key` header so a retry
    after a network error returns the first payment instead of recording it twice. Only `notes` can be
    edited; amounts never change.
    """

    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    filterset_class = PaymentFilter
    search_fields = ["payer__full_name", "payer__mobile", "reference_number", "receipts__receipt_number"]
    ordering_fields = ["paid_at", "amount", "created_at"]
    required_permissions = {
        "list": "payments.view",
        "retrieve": "payments.view",
        "create": "payments.create",
        "partial_update": "payments.create",
        "confirm": "payments.create",
        "cancel": "payments.cancel_pending",
        "fail": "payments.cancel_pending",
    }

    def get_serializer_class(self):
        if self.action == "create":
            return PaymentCreateSerializer
        if self.action == "partial_update":
            return PaymentNotesSerializer
        if self.action in ("confirm", "cancel", "fail"):
            return PaymentStatusChangeSerializer
        return PaymentSerializer

    def get_base_queryset(self):
        return (
            Payment.objects.for_org(self.organization)
            .select_related("event", "payer", "collector__user")
            .prefetch_related("lines__contribution_type", "lines__fund", "receipts")
            .distinct()
        )

    def scope_queryset(self, queryset):
        if self.action in ("confirm", "partial_update") and self.org_context.scope("payments.create") != SCOPE_ALL:
            queryset = queryset.filter(collector=self.membership)
        return scope_money(queryset, self.org_context, "payments.view", self.request.user, person="payer")

    def _check_can_collect(self):
        if self.org_context.scope("payments.create") == SCOPE_ALL:
            return
        # Collectors collect from people assigned to them (Phase 3). Until assignments exist they can collect
        # only when the organization allows collecting from anyone.
        if not (self.organization.settings or {}).get("allow_unassigned_collection"):
            raise PermissionDenied(_("Your organization has not allowed collecting from unassigned people."))

    def _detail(self, payment, status_code=status.HTTP_200_OK):
        payment = self.get_base_queryset().get(pk=payment.pk)
        return Response(PaymentSerializer(payment, context=self.get_serializer_context()).data, status=status_code)

    @extend_schema(request=PaymentCreateSerializer, responses={201: PaymentSerializer, 200: PaymentSerializer})
    def create(self, request, *args, **kwargs):
        self._check_can_collect()
        serializer = PaymentCreateSerializer(data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        key = request.META.get("HTTP_IDEMPOTENCY_KEY") or data.get("idempotency_key") or None
        payment, created = services.record_payment(
            org=self.organization,
            event=data["event"],
            payer=data["payer"],
            mode=data["mode"],
            status=data["status"],
            paid_at=data.get("paid_at"),
            amount=data.get("amount"),
            reference_number=data["reference_number"],
            cheque_bank=data["cheque_bank"],
            cheque_date=data.get("cheque_date"),
            notes=data["notes"],
            lines=[services.LineInput(**line) for line in data["lines"]],
            collector=self.membership,
            idempotency_key=key,
            request=request,
            actor=request.user,
        )
        return self._detail(payment, status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @extend_schema(request=PaymentNotesSerializer, responses=PaymentSerializer)
    def partial_update(self, request, *args, **kwargs):
        super().partial_update(request, *args, **kwargs)
        return self._detail(self.get_object())

    def _status_action(self, request, func):
        payment = self.get_object()
        serializer = PaymentStatusChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        kwargs = {"request": request, "actor": request.user}
        if func is not services.confirm_payment:
            kwargs["reason"] = serializer.validated_data["reason"]
        return self._detail(func(payment, **kwargs))

    @extend_schema(request=PaymentStatusChangeSerializer, responses=PaymentSerializer)
    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        """Pending → successful (e.g. a cheque cleared). Issues the receipt."""
        return self._status_action(request, services.confirm_payment)

    @extend_schema(request=PaymentStatusChangeSerializer, responses=PaymentSerializer)
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Pending → cancelled. Successful payments are corrected through their receipt instead."""
        return self._status_action(request, services.cancel_payment)

    @extend_schema(request=PaymentStatusChangeSerializer, responses=PaymentSerializer)
    @action(detail=True, methods=["post"])
    def fail(self, request, pk=None):
        """Pending → failed (e.g. a bounced cheque)."""
        return self._status_action(request, services.fail_payment)
