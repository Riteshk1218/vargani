import django_filters
from django.core.files.storage import default_storage
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_noop
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.core.admin_override import ADMIN_EDIT
from apps.core.downloads import Col, ListDownloadMixin
from apps.core.tenancy import SCOPE_ALL
from apps.core.viewsets import TenantModelViewSet

from . import attachments, services
from .models import Expense, ExpenseCategory, OtherIncome
from .serializers import (
    AttachmentUploadSerializer,
    ExpenseAttachmentSerializer,
    ExpenseCategorySerializer,
    ExpenseReasonSerializer,
    ExpenseSerializer,
    OtherIncomeNotesSerializer,
    OtherIncomeSerializer,
)


class ExpenseCategoryViewSet(TenantModelViewSet):
    """Expense categories. Archive with PATCH {"is_active": false}; never deleted."""

    queryset = ExpenseCategory.objects.all()
    serializer_class = ExpenseCategorySerializer
    filterset_fields = ["is_active"]
    search_fields = ["name"]
    pagination_class = None
    required_permissions = {
        "list": ("expenses.view", "expenses.create"),
        "retrieve": ("expenses.view", "expenses.create"),
        "create": "expenses.approve",
        "partial_update": "expenses.approve",
    }


class ExpenseFilter(django_filters.FilterSet):
    date_from = django_filters.DateFilter(field_name="expense_date", lookup_expr="gte")
    date_to = django_filters.DateFilter(field_name="expense_date", lookup_expr="lte")

    class Meta:
        model = Expense
        fields = ["event", "category", "status", "mode"]


class ExpenseViewSet(ListDownloadMixin, TenantModelViewSet):
    """Expenses with bills and an approval flow. Only approved expenses count in the balance.

    Editable while draft, submitted or rejected. Approved expenses can only be voided (with a reason).
    Collectors see and change only the expenses they entered. An Organization Admin can edit any expense and
    delete it with DELETE.
    """

    queryset = Expense.objects.all()
    download_title = gettext_noop("Expenses")
    download_columns = [
        Col("expense_date", gettext_noop("Date"), "date"),
        Col("event_name", gettext_noop("Event")),
        Col("category_name", gettext_noop("Category")),
        Col("payee", gettext_noop("Paid to")),
        Col("description", gettext_noop("Description")),
        Col("mode", gettext_noop("Payment mode"), "mode"),
        Col("reference_number", gettext_noop("Reference")),
        Col("status", gettext_noop("Status"), "status"),
        Col("decided_by_name", gettext_noop("Approved by")),
        Col("amount", gettext_noop("Amount"), "money"),
    ]
    serializer_class = ExpenseSerializer
    filterset_class = ExpenseFilter
    search_fields = ["payee", "description", "reference_number", "category__name"]
    ordering_fields = ["expense_date", "amount", "created_at"]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    required_permissions = {
        "list": "expenses.view",
        "retrieve": "expenses.view",
        "create": "expenses.create",
        "partial_update": "expenses.create",
        "submit": "expenses.create",
        "approve": "expenses.approve",
        "reject": "expenses.approve",
        "void": "expenses.create",
        "attachments": "expenses.create",
        "attachment": ("expenses.view", "expenses.create"),
        "destroy": ADMIN_EDIT,
    }

    def get_required_permissions(self):
        if self.action is None:
            return ()  # a method this route does not offer: answer 405
        return super().get_required_permissions()

    @property
    def is_admin(self):
        return self.org_context.has(ADMIN_EDIT)

    def scope_queryset(self, queryset):
        if self.org_context.scope("expenses.view") == SCOPE_ALL or self.org_context.has("expenses.approve"):
            return queryset
        return queryset.filter(created_by=self.request.user)

    def get_base_queryset(self):
        return (
            super()
            .get_base_queryset()
            .select_related("category", "event", "created_by", "submitted_by", "decided_by", "voided_by")
            .prefetch_related("attachments")
        )

    def _detail(self, expense, code=status.HTTP_200_OK):
        return Response(
            ExpenseSerializer(self.get_queryset().get(pk=expense.pk), context=self.get_serializer_context()).data,
            status=code,
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        expense = services.create_expense(
            org=self.organization, data=serializer.validated_data, request=request, actor=request.user
        )
        return self._detail(expense, status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        expense = self.get_object()
        serializer = self.get_serializer(expense, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        services.update_expense(
            expense, data=serializer.validated_data, admin=self.is_admin, request=request, actor=request.user
        )
        return self._detail(expense)

    def destroy(self, request, *args, **kwargs):
        """Organization Admin: delete an expense and its bills (a copy stays in the audit log)."""
        services.delete_expense(self.get_object(), request=request, actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(request=None, responses=ExpenseSerializer)
    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        return self._detail(services.submit(self.get_object(), request=request, actor=request.user))

    @extend_schema(request=None, responses=ExpenseSerializer)
    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        expense = services.approve(
            self.get_object(), approver_membership=self.membership, request=request, actor=request.user
        )
        return self._detail(expense)

    @extend_schema(request=ExpenseReasonSerializer, responses=ExpenseSerializer)
    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        serializer = ExpenseReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        expense = services.reject(
            self.get_object(), reason=serializer.validated_data["reason"], request=request, actor=request.user
        )
        return self._detail(expense)

    @extend_schema(request=ExpenseReasonSerializer, responses=ExpenseSerializer)
    @action(detail=True, methods=["post"])
    def void(self, request, pk=None):
        serializer = ExpenseReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        expense = services.void_expense(
            self.get_object(),
            reason=serializer.validated_data["reason"],
            can_approve=self.org_context.has("expenses.approve"),
            request=request,
            actor=request.user,
        )
        return self._detail(expense)

    @extend_schema(request={"multipart/form-data": AttachmentUploadSerializer}, responses=ExpenseAttachmentSerializer)
    @action(detail=True, methods=["post"], parser_classes=[MultiPartParser])
    def attachments(self, request, pk=None):
        """Upload a bill (JPG, PNG, WEBP or PDF, at most 10 MB; 10 per expense)."""
        attachment = attachments.add(
            self.get_object(), request.FILES.get("file"), admin=self.is_admin, request=request, actor=request.user
        )
        return Response(ExpenseAttachmentSerializer(attachment).data, status=status.HTTP_201_CREATED)

    @extend_schema(responses={(200, "application/octet-stream"): OpenApiTypes.BINARY})
    @action(detail=True, methods=["get", "delete"], url_path=r"attachments/(?P<attachment_id>[0-9a-f-]+)")
    def attachment(self, request, pk=None, attachment_id=None):
        """GET downloads the file; DELETE removes it while the expense can still change."""
        expense = self.get_object()
        item = get_object_or_404(expense.attachments.all(), pk=attachment_id)
        if request.method == "DELETE":
            if not self.org_context.has("expenses.create"):
                from rest_framework.exceptions import PermissionDenied

                raise PermissionDenied()
            attachments.remove(item, admin=self.is_admin, request=request, actor=request.user)
            return Response(status=status.HTTP_204_NO_CONTENT)
        response = FileResponse(
            default_storage.open(item.file, "rb"),
            content_type=item.content_type,
            as_attachment=request.query_params.get("inline") != "1",
            filename=item.original_name,
        )
        response["X-Content-Type-Options"] = "nosniff"
        response["Cache-Control"] = "private, no-store"
        return response


class OtherIncomeFilter(django_filters.FilterSet):
    date_from = django_filters.DateFilter(field_name="received_on", lookup_expr="gte")
    date_to = django_filters.DateFilter(field_name="received_on", lookup_expr="lte")

    class Meta:
        model = OtherIncome
        fields = ["event", "fund", "source", "status", "mode"]


class OtherIncomeViewSet(ListDownloadMixin, TenantModelViewSet):
    """Income not from a person (donation box, sponsorship, interest, sales). Amounts never change; void instead.

    An Organization Admin can change every field with PATCH and delete with DELETE.
    """

    queryset = OtherIncome.objects.all()
    download_title = gettext_noop("Other income")
    download_columns = [
        Col("received_on", gettext_noop("Date"), "date"),
        Col("source", gettext_noop("Source"), "source"),
        Col("fund_name", gettext_noop("Fund")),
        Col("description", gettext_noop("Description")),
        Col("mode", gettext_noop("Payment mode"), "mode"),
        Col("reference_number", gettext_noop("Reference")),
        Col("status", gettext_noop("Status"), "status"),
        Col("amount", gettext_noop("Amount"), "money"),
    ]
    serializer_class = OtherIncomeSerializer
    filterset_class = OtherIncomeFilter
    search_fields = ["description", "reference_number"]
    ordering_fields = ["received_on", "amount", "created_at"]
    required_permissions = {
        "list": "other_income.manage",
        "retrieve": "other_income.manage",
        "create": "other_income.manage",
        "partial_update": "other_income.manage",
        "void": "other_income.manage",
        "destroy": ADMIN_EDIT,
    }
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_base_queryset(self):
        return super().get_base_queryset().select_related("fund", "created_by", "voided_by")

    def get_serializer_class(self):
        if self.action == "partial_update" and not self.org_context.has(ADMIN_EDIT):
            return OtherIncomeNotesSerializer
        return OtherIncomeSerializer

    def _detail(self, income, code=status.HTTP_200_OK):
        data = OtherIncomeSerializer(self.get_queryset().get(pk=income.pk), context=self.get_serializer_context()).data
        return Response(data, status=code)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        income = services.record_income(
            org=self.organization, data=serializer.validated_data, request=request, actor=request.user
        )
        return self._detail(income, status.HTTP_201_CREATED)

    @extend_schema(request=OtherIncomeNotesSerializer, responses=OtherIncomeSerializer)
    def partial_update(self, request, *args, **kwargs):
        if self.org_context.has(ADMIN_EDIT):
            income = self.get_object()
            serializer = OtherIncomeSerializer(
                income, data=request.data, partial=True, context=self.get_serializer_context()
            )
            serializer.is_valid(raise_exception=True)
            services.update_income(income, data=serializer.validated_data, request=request, actor=request.user)
            return self._detail(income)
        super().partial_update(request, *args, **kwargs)
        return self._detail(self.get_object())

    def destroy(self, request, *args, **kwargs):
        services.delete_income(self.get_object(), request=request, actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(request=ExpenseReasonSerializer, responses=OtherIncomeSerializer)
    @action(detail=True, methods=["post"])
    def void(self, request, pk=None):
        serializer = ExpenseReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        income = services.void_income(
            self.get_object(), reason=serializer.validated_data["reason"], request=request, actor=request.user
        )
        return self._detail(income)
