from decimal import Decimal

from rest_framework import serializers

from apps.contributions.models import Contribution, ContributionType
from apps.core.fields import TenantPrimaryKeyRelatedField
from apps.events.models import Event
from apps.people.models import Person
from apps.receipts.models import Receipt

from .models import Payment, PaymentMode

MONEY = {"max_digits": 12, "decimal_places": 2}


class PaymentLineInputSerializer(serializers.Serializer):
    contribution_type = TenantPrimaryKeyRelatedField(queryset=ContributionType.objects.all())
    amount = serializers.DecimalField(**MONEY, min_value=Decimal("0.01"))
    period_month = serializers.DateField(required=False, allow_null=True)
    notes = serializers.CharField(max_length=300, required=False, allow_blank=True, default="")


class PaymentCreateSerializer(serializers.Serializer):
    event = TenantPrimaryKeyRelatedField(queryset=Event.objects.filter(deleted_at__isnull=True))
    payer = TenantPrimaryKeyRelatedField(queryset=Person.objects.filter(deleted_at__isnull=True))
    mode = serializers.ChoiceField(choices=PaymentMode.choices)
    status = serializers.ChoiceField(
        choices=[Payment.Status.SUCCESSFUL, Payment.Status.PENDING], default=Payment.Status.SUCCESSFUL
    )
    paid_at = serializers.DateTimeField(required=False, allow_null=True)
    amount = serializers.DecimalField(**MONEY, min_value=Decimal("0.01"), required=False, allow_null=True)
    reference_number = serializers.CharField(max_length=60, required=False, allow_blank=True, default="")
    cheque_bank = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    cheque_date = serializers.DateField(required=False, allow_null=True)
    notes = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")
    idempotency_key = serializers.CharField(max_length=100, required=False, allow_blank=True)
    lines = PaymentLineInputSerializer(many=True, allow_empty=False, max_length=36)

    def validate_reference_number(self, value):
        return value.strip()


class PaymentLineSerializer(serializers.ModelSerializer):
    contribution_type_name = serializers.CharField(source="contribution_type.name", read_only=True)
    fund_name = serializers.CharField(source="fund.name", read_only=True, default=None)

    class Meta:
        model = Contribution
        fields = [
            "id",
            "contribution_type",
            "contribution_type_name",
            "fund",
            "fund_name",
            "period_month",
            "amount",
            "status",
            "notes",
        ]
        read_only_fields = fields


class ReceiptRefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Receipt
        fields = ["id", "receipt_number", "status", "issued_at"]
        read_only_fields = fields


class PaymentSerializer(serializers.ModelSerializer):
    event_name = serializers.CharField(source="event.name", read_only=True)
    payer_name = serializers.CharField(source="payer.full_name", read_only=True)
    payer_mobile = serializers.CharField(source="payer.mobile", read_only=True)
    collector_name = serializers.SerializerMethodField()
    lines = PaymentLineSerializer(many=True, read_only=True)
    receipt = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            "id",
            "event",
            "event_name",
            "payer",
            "payer_name",
            "payer_mobile",
            "amount",
            "mode",
            "status",
            "paid_at",
            "reference_number",
            "cheque_bank",
            "cheque_date",
            "collector_name",
            "notes",
            "status_reason",
            "lines",
            "receipt",
            "created_at",
        ]
        read_only_fields = [f for f in fields if f != "notes"]

    def get_collector_name(self, obj) -> str | None:
        return obj.collector.user.full_name if obj.collector else None

    def get_receipt(self, obj) -> dict | None:
        receipts = sorted(obj.receipts.all(), key=lambda r: (r.status != Receipt.Status.ISSUED, -r.sequence))
        return ReceiptRefSerializer(receipts[0]).data if receipts else None


class PaymentNotesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ["notes"]


class PaymentStatusChangeSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=300, required=False, allow_blank=True, default="")
