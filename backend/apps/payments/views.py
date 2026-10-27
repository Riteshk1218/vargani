import django_filters
from django.utils.translation import gettext as _
from django.utils.translation import gettext_noop
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.contributions import assignments
from apps.core.dates import OrgDayFilter
from apps.core.downloads import Col, ListDownloadMixin
from apps.core.scoping import scope_money
from apps.core.tenancy import SCOPE_ALL
from apps.core.viewsets import TenantModelViewSet
from apps.organizations import form_studio

from . import admin_edit, followups, services
from .models import Payment
from .serializers import (
    PaymentAdminEditSerializer,
    PaymentCreateSerializer,
    PaymentDeleteSerializer,
    PaymentNotesSerializer,
    PaymentSerializer,
    PaymentStatusChangeSerializer,
    PaymentVisitSerializer,
)


class PaymentFilter(django_filters.FilterSet):
    date_from = OrgDayFilter(field_name="paid_at")
    date_to = OrgDayFilter(field_name="paid_at", end=True)
    pavti = django_filters.ChoiceFilter(
        method="filter_pavti",
        choices=[(v, v) for v in ("unpaid", "partly_paid", "owing", "paid")],
        label="Pavti status: unpaid, partly_paid, owing (either) or paid",
    )
    follow_up = django_filters.ChoiceFilter(
        method="filter_follow_up",
        choices=[(v, v) for v in ("overdue", "today", "upcoming", "none")],
        label="Pavtis still owing whose follow-up date has passed (overdue), is today, is later, or is not set",
    )

    def filter_pavti(self, queryset, name, value):
        return followups.filter_pavti(queryset, value)

    def filter_follow_up(self, queryset, name, value):
        return followups.filter_follow_up(queryset, value, followups.org_today(self.request._org_context.organization))

    class Meta:
        model = Payment
        fields = ["event", "status", "mode", "payer", "collector"]


class PaymentViewSet(ListDownloadMixin, TenantModelViewSet):
    """Payments with their contribution lines and receipt.

    POST records a payment (also exposed as POST /collections/). Send an `Idempotency-Key` header so a retry
    after a network error returns the first payment instead of recording it twice. `payer` is optional: leave
    it empty for an anonymous collection, or send `new_person` to add the contributor while collecting.

    PATCH edits only `notes`. An Organization Admin can edit everything with POST /payments/{id}/edit/ and
    delete with DELETE /payments/{id}/ (the receipt is voided; the record stays in the audit log).
    """

    queryset = Payment.objects.all()
    download_title = gettext_noop("Payments")
    download_columns = [
        Col("paid_at", gettext_noop("Date"), "datetime"),
        Col("payer_name", gettext_noop("Name")),
        Col("payer_mobile", gettext_noop("Mobile")),
        Col("event_name", gettext_noop("Event")),
        Col("mode", gettext_noop("Payment mode"), "mode"),
        Col("reference_number", gettext_noop("Reference")),
        Col("collector_name", gettext_noop("Collected by")),
        Col("status", gettext_noop("Status"), "status"),
        Col("amount", gettext_noop("Amount"), "money"),
        Col("balance_due", gettext_noop("Still owed"), "money"),
        Col("follow_up_on", gettext_noop("Follow-up date"), "date"),
        Col("created_at", gettext_noop("Created at"), "datetime"),
        Col("created_by_name", gettext_noop("Created by")),
    ]
    serializer_class = PaymentSerializer
    filterset_class = PaymentFilter
    search_fields = ["payer__full_name", "payer__mobile", "reference_number", "receipts__receipt_number"]
    ordering_fields = ["paid_at", "amount", "created_at", "follow_up_on", "balance_due", "payer__full_name"]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    required_permissions = {
        "list": "payments.view",
        "retrieve": "payments.view",
        "create": "payments.create",
        "partial_update": "payments.create",
        "confirm": "payments.create",
        "visit": "payments.create",
        "cancel": "payments.cancel_pending",
        "fail": "payments.cancel_pending",
        "admin_edit": "records.admin_edit",
        "destroy": "records.admin_edit",
    }

    def get_serializer_class(self):
        if self.action == "create":
            return PaymentCreateSerializer
        if self.action == "partial_update":
            return PaymentNotesSerializer
        if self.action in ("confirm", "cancel", "fail"):
            return PaymentStatusChangeSerializer
        if self.action == "visit":
            return PaymentVisitSerializer
        return PaymentSerializer

    def get_base_queryset(self):
        return followups.with_pavti_balance(
            Payment.objects.for_org(self.organization)
            .select_related("event", "payer", "collector__user", "organization", "created_by")
            .prefetch_related("lines__contribution_type", "lines__fund", "receipts")
            .distinct()
        )

    def scope_queryset(self, queryset):
        if self.action == "list" and not self.request.query_params.get("status"):
            queryset = queryset.exclude(status=Payment.Status.DELETED)
        if self.action in ("confirm", "partial_update") and self.org_context.scope("payments.create") != SCOPE_ALL:
            queryset = queryset.filter(collector=self.membership)
        return scope_money(queryset, self.org_context, "payments.view", self.request.user, person="payer")

    def _check_can_collect(self, payer=None, event=None, new_person=False):
        if new_person and not (self.org_context.has("people.create") or self.org_context.has("people.manage")):
            raise PermissionDenied(_("You cannot add new people."))
        if self.org_context.scope("payments.create") == SCOPE_ALL:
            return
        if payer is None:
            return  # anonymous collection, or a new person who is assigned to this collector on the spot
        if (self.organization.settings or {}).get("allow_unassigned_collection"):
            return
        # Collectors collect only from people assigned to them in this event.
        if not assignments.is_assigned(membership=self.membership, person=payer, event=event):
            raise PermissionDenied(_("This person is not assigned to you for this event."))

    def _detail(self, payment, status_code=status.HTTP_200_OK):
        payment = self.get_base_queryset().get(pk=payment.pk)
        return Response(PaymentSerializer(payment, context=self.get_serializer_context()).data, status=status_code)

    @extend_schema(request=PaymentCreateSerializer, responses={201: PaymentSerializer, 200: PaymentSerializer})
    def create(self, request, *args, **kwargs):
        serializer = PaymentCreateSerializer(data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        self._check_can_collect(data["payer"], data["event"], new_person=bool(data["new_person"]))
        replaces = data.get("replaces_receipt")
        if replaces is not None and not self.org_context.has("receipts.void_approve"):
            raise PermissionDenied()
        key = request.META.get("HTTP_IDEMPOTENCY_KEY") or data.get("idempotency_key") or None
        payment, created = services.record_payment(
            org=self.organization,
            event=data["event"],
            payer=data["payer"],
            new_person=data["new_person"],
            assign_new_person=self.org_context.scope("people.view") != SCOPE_ALL,
            mode=data["mode"],
            status=data["status"],
            paid_at=data.get("paid_at"),
            amount=data.get("amount"),
            reference_number=data["reference_number"],
            cheque_bank=data["cheque_bank"],
            cheque_date=data.get("cheque_date"),
            notes=data["notes"],
            lines=[services.LineInput(**line) for line in data["lines"]],
            received=data.get("received"),
            follow_up_on=data.get("follow_up_on"),
            custom_fields=form_studio.clean_values(self.organization, data["custom_fields"]),
            collector=self.membership,
            idempotency_key=key,
            replaces_receipt=replaces,
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

    @extend_schema(request=PaymentVisitSerializer, responses=PaymentSerializer)
    @action(detail=True, methods=["post"])
    def visit(self, request, pk=None):
        """A later visit to the same pavti (door-to-door follow-up). No new pavti is made.

        `received` (may be 0) is added to this pavti towards what is still owed, and `follow_up_on` is the next
        visit; it is cleared once nothing is owed. Money taken in another mode than the pavti's is noted on its
        line.
        """
        payment = self.get_object()
        if payment.payer_id:
            self._check_can_collect(payment.payer, payment.event)
        serializer = PaymentVisitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        payment = followups.record_visit(
            payment,
            received=data["received"],
            mode=data["mode"],
            reference_number=data["reference_number"],
            follow_up_on=data["follow_up_on"],
            collector=self.membership,
            request=request,
            actor=request.user,
        )
        return self._detail(payment)

    @extend_schema(request=PaymentAdminEditSerializer, responses=PaymentSerializer)
    @action(detail=True, methods=["post"], url_path="edit")
    def admin_edit(self, request, pk=None):
        """Organization Admin: change the person, amount and lines, mode, date and time or notes.

        The receipt keeps its number and shows the new details. Old and new values go to the audit log.
        """
        payment = self.get_object()
        serializer = PaymentAdminEditSerializer(data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        if "lines" in data:
            data["lines"] = [services.LineInput(**line) for line in data["lines"]]
        return self._detail(admin_edit.edit_payment(payment, data=data, request=request, actor=request.user))

    @extend_schema(request=PaymentDeleteSerializer, responses=PaymentSerializer)
    def destroy(self, request, *args, **kwargs):
        """Organization Admin: delete a collection. It leaves every list and total; its receipt is voided."""
        serializer = PaymentDeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment = admin_edit.delete_payment(
            self.get_object(), reason=serializer.validated_data["reason"], request=request, actor=request.user
        )
        return self._detail(payment)
