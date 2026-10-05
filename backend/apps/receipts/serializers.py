from django.core.files.storage import default_storage
from rest_framework import serializers

from .models import Receipt


class ReceiptSerializer(serializers.ModelSerializer):
    payer = serializers.UUIDField(source="payment.payer_id", read_only=True)
    payer_name = serializers.CharField(source="payment.payer.full_name", read_only=True)
    amount = serializers.DecimalField(source="payment.amount", max_digits=12, decimal_places=2, read_only=True)
    mode = serializers.CharField(source="payment.mode", read_only=True)
    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = Receipt
        fields = [
            "id",
            "receipt_number",
            "status",
            "issued_at",
            "language",
            "event",
            "payment",
            "payer",
            "payer_name",
            "amount",
            "mode",
            "void_reason",
            "voided_at",
            "replaces_receipt",
            "snapshot",
            "logo_url",
        ]
        read_only_fields = fields

    def get_logo_url(self, obj) -> str | None:
        key = (obj.snapshot.get("organization") or {}).get("logo")
        if not key:
            return None
        url = default_storage.url(key)
        request = self.context.get("request")
        if request is not None and url.startswith("/"):
            return request.build_absolute_uri(url)
        return url
