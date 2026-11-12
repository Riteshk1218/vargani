from django.core.files.storage import default_storage
from rest_framework import serializers

from apps.core.serializers import CreatedByMixin

from .models import Receipt, ReceiptVoidRequest


class ReceiptSerializer(CreatedByMixin, serializers.ModelSerializer):
    payer = serializers.UUIDField(source="payment.payer_id", read_only=True)
    payer_name = serializers.CharField(source="payment.payer_name", read_only=True)
    amount = serializers.DecimalField(source="payment.amount", max_digits=12, decimal_places=2, read_only=True)
    mode = serializers.CharField(source="payment.mode", read_only=True)
    paid_at = serializers.DateTimeField(source="payment.paid_at", read_only=True)
    logo_url = serializers.SerializerMethodField()
    replaces_receipt_number = serializers.CharField(
        source="replaces_receipt.receipt_number", default=None, read_only=True
    )
    replaced_by = serializers.SerializerMethodField()
    pending_void_request = serializers.SerializerMethodField()
    created_by = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()

    def _creator(self, obj):
        """Who created the pavti: the person who recorded the collection (falls back to the receipt)."""
        return obj.payment.created_by or obj.created_by

    def get_created_by(self, obj) -> str | None:
        user = self._creator(obj)
        return str(user.pk) if user else None

    def get_created_by_name(self, obj) -> str | None:
        user = self._creator(obj)
        return (user.full_name or user.username) if user else None

    def get_can_edit(self, obj) -> bool:
        """The caller may edit this pavti in place (same number): an Organization Admin or its creator."""
        from apps.payments.admin_edit import can_edit

        if obj.status != Receipt.Status.ISSUED:
            return False
        request = self.context.get("request")
        return can_edit(obj.payment, getattr(request, "_org_context", None), getattr(request, "user", None))

    def get_replaced_by(self, obj) -> dict | None:
        new = obj.replaced_by.first()
        return {"id": str(new.pk), "receipt_number": new.receipt_number} if new else None

    def get_pending_void_request(self, obj) -> dict | None:
        pending = obj.void_requests.filter(status="pending").first()
        return {"id": str(pending.pk), "reason": pending.reason} if pending else None

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
            "paid_at",
            "void_reason",
            "voided_at",
            "replaces_receipt",
            "replaces_receipt_number",
            "replaced_by",
            "pending_void_request",
            "snapshot",
            "logo_url",
            "created_at",
            "created_by",
            "created_by_name",
            "can_edit",
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


class ReceiptVoidRequestSerializer(serializers.ModelSerializer):
    receipt_number = serializers.CharField(source="receipt.receipt_number", read_only=True)
    payer_name = serializers.CharField(source="receipt.payment.payer_name", read_only=True)
    amount = serializers.DecimalField(source="receipt.payment.amount", max_digits=12, decimal_places=2, read_only=True)
    requested_by_name = serializers.CharField(source="requested_by.full_name", read_only=True)
    decided_by_name = serializers.CharField(source="decided_by.full_name", read_only=True, default=None)

    class Meta:
        model = ReceiptVoidRequest
        fields = [
            "id",
            "receipt",
            "receipt_number",
            "payer_name",
            "amount",
            "reason",
            "status",
            "requested_by_name",
            "decided_by_name",
            "decided_at",
            "decision_note",
            "created_at",
        ]
        read_only_fields = fields
