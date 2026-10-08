from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.core.fields import TenantPrimaryKeyRelatedField
from apps.core.serializers import ImmutableFieldsMixin
from apps.events.models import Event
from apps.funds.models import Fund
from apps.payments.models import PaymentMode

from .models import Expense, ExpenseAttachment, ExpenseCategory, OtherIncome

MANUAL_MODES = [m for m in PaymentMode.values if m != PaymentMode.ONLINE]


def _user_name(user):
    return user.full_name if user else None


def _clean(value):
    return " ".join((value or "").split())


class ExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = ["id", "name", "is_default", "is_active", "created_at"]
        read_only_fields = ["id", "is_default", "created_at"]

    def validate_name(self, value):
        value = _clean(value)
        if not value:
            raise serializers.ValidationError(_("Enter a name."))
        org = self.context["organization"]
        siblings = ExpenseCategory.objects.filter(organization=org, name__iexact=value)
        if self.instance:
            siblings = siblings.exclude(pk=self.instance.pk)
        if siblings.exists():
            raise serializers.ValidationError(_("A category with this name already exists."))
        return value


class ExpenseAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseAttachment
        fields = ["id", "original_name", "content_type", "size_bytes", "created_at"]
        read_only_fields = fields


class ExpenseSerializer(ImmutableFieldsMixin, serializers.ModelSerializer):
    event = TenantPrimaryKeyRelatedField(queryset=Event.objects.filter(deleted_at__isnull=True))
    category = TenantPrimaryKeyRelatedField(queryset=ExpenseCategory.objects.filter(is_active=True))
    mode = serializers.ChoiceField(choices=MANUAL_MODES, default=PaymentMode.CASH)
    category_name = serializers.CharField(source="category.name", read_only=True)
    event_name = serializers.CharField(source="event.name", read_only=True)
    created_by_name = serializers.SerializerMethodField()
    submitted_by_name = serializers.SerializerMethodField()
    decided_by_name = serializers.SerializerMethodField()
    voided_by_name = serializers.SerializerMethodField()
    attachments = ExpenseAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Expense
        fields = [
            "id",
            "event",
            "event_name",
            "financial_year",
            "category",
            "category_name",
            "amount",
            "expense_date",
            "expense_time",
            "mode",
            "payee",
            "description",
            "reference_number",
            "status",
            "created_by",
            "created_by_name",
            "submitted_by",
            "submitted_by_name",
            "submitted_at",
            "decided_by",
            "decided_by_name",
            "decided_at",
            "rejection_reason",
            "void_reason",
            "voided_by_name",
            "voided_at",
            "attachments",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            f
            for f in fields
            if f
            not in {
                "event",
                "category",
                "amount",
                "expense_date",
                "expense_time",
                "mode",
                "payee",
                "description",
                "reference_number",
            }
        ]
        extra_kwargs = {"expense_date": {"required": False}, "payee": {"required": False}}

    def get_created_by_name(self, obj) -> str | None:
        return _user_name(obj.created_by)

    def get_submitted_by_name(self, obj) -> str | None:
        return _user_name(obj.submitted_by)

    def get_decided_by_name(self, obj) -> str | None:
        return _user_name(obj.decided_by)

    def get_voided_by_name(self, obj) -> str | None:
        return _user_name(obj.voided_by)

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError(_("Amount must be more than zero."))
        return value

    def validate_payee(self, value):
        return _clean(value)


class ExpenseReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=300, required=False, allow_blank=True, default="")


class AttachmentUploadSerializer(serializers.Serializer):
    file = serializers.FileField()


class OtherIncomeSerializer(ImmutableFieldsMixin, serializers.ModelSerializer):
    event = TenantPrimaryKeyRelatedField(queryset=Event.objects.filter(deleted_at__isnull=True))
    fund = TenantPrimaryKeyRelatedField(queryset=Fund.objects.all(), required=False, allow_null=True)
    mode = serializers.ChoiceField(choices=MANUAL_MODES, default=PaymentMode.CASH)
    fund_name = serializers.CharField(source="fund.name", read_only=True, default=None)
    created_by_name = serializers.SerializerMethodField()
    voided_by_name = serializers.SerializerMethodField()

    class Meta:
        model = OtherIncome
        fields = [
            "id",
            "event",
            "financial_year",
            "fund",
            "fund_name",
            "source",
            "amount",
            "received_on",
            "mode",
            "reference_number",
            "description",
            "status",
            "void_reason",
            "voided_by_name",
            "voided_at",
            "created_by_name",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "financial_year",
            "status",
            "void_reason",
            "voided_by_name",
            "voided_at",
            "created_at",
        ]

    def get_created_by_name(self, obj) -> str | None:
        return _user_name(obj.created_by)

    def get_voided_by_name(self, obj) -> str | None:
        return _user_name(obj.voided_by)

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError(_("Amount must be more than zero."))
        return value


class OtherIncomeNotesSerializer(serializers.ModelSerializer):
    class Meta:
        model = OtherIncome
        fields = ["description", "reference_number"]
