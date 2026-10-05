from django.db import models
from django.db.models import Q

from apps.core.models import TenantModel


class PaymentMode(models.TextChoices):
    CASH = "cash"
    UPI = "upi"
    BANK_TRANSFER = "bank_transfer"
    CHEQUE = "cheque"
    ONLINE = "online"
    OTHER = "other"


class Payment(TenantModel):
    """Money received from one person at one time. It settles one or more contribution lines.

    Never deleted. A pending payment can be cancelled or marked failed; a successful one is corrected only
    through its receipt (void + new receipt, Phase 3).
    """

    class Status(models.TextChoices):
        PENDING = "pending"
        SUCCESSFUL = "successful"
        FAILED = "failed"
        CANCELLED = "cancelled"
        REFUNDED = "refunded"

    financial_year = models.ForeignKey("organizations.FinancialYear", on_delete=models.PROTECT, related_name="+")
    event = models.ForeignKey("events.Event", on_delete=models.PROTECT, related_name="payments")
    payer = models.ForeignKey("people.Person", on_delete=models.PROTECT, related_name="payments")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    mode = models.CharField(max_length=20, choices=PaymentMode.choices)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.SUCCESSFUL)
    paid_at = models.DateTimeField()
    reference_number = models.CharField(max_length=60, blank=True, help_text="UPI ref / UTR / cheque number")
    cheque_bank = models.CharField(max_length=100, blank=True)
    cheque_date = models.DateField(null=True, blank=True)
    collector = models.ForeignKey(
        "organizations.OrganizationMembership", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    gateway = models.CharField(max_length=20, blank=True)
    gateway_order_id = models.CharField(max_length=100, null=True, blank=True)
    gateway_payment_id = models.CharField(max_length=100, null=True, blank=True)
    gateway_payload = models.JSONField(null=True, blank=True)
    idempotency_key = models.CharField(max_length=100, null=True, blank=True)
    notes = models.CharField(max_length=500, blank=True)
    status_reason = models.CharField(max_length=300, blank=True)
    status_changed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-paid_at", "-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "id"], name="payment_org_id_unique"),
            models.UniqueConstraint(fields=["event", "id"], name="payment_event_id_unique"),
            models.UniqueConstraint(
                fields=["organization", "idempotency_key"],
                condition=Q(idempotency_key__isnull=False),
                name="payment_idempotency_unique",
            ),
            models.UniqueConstraint(
                fields=["gateway", "gateway_payment_id"],
                condition=Q(gateway_payment_id__isnull=False),
                name="payment_gateway_payment_unique",
            ),
            models.CheckConstraint(condition=Q(amount__gt=0), name="payment_amount_positive"),
        ]
        indexes = [
            models.Index(fields=["organization", "event", "status", "paid_at"], name="payment_org_event_idx"),
            models.Index(fields=["organization", "collector", "paid_at"], name="payment_org_collector_idx"),
            models.Index(fields=["organization", "event", "mode"], name="payment_org_mode_idx"),
        ]

    def __str__(self):
        return f"{self.amount} {self.mode}"
