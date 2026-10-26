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
    """Money received at one time, from a person or anonymously (no payer). It settles one or more lines.

    Never removed from the database. A pending payment can be cancelled or marked failed; a successful one is
    corrected through its receipt (void + new receipt), or edited / deleted by an Organization Admin
    (payments/admin_edit.py), which keeps the receipt number and records every change in the audit log.
    """

    class Status(models.TextChoices):
        PENDING = "pending"
        SUCCESSFUL = "successful"
        FAILED = "failed"
        CANCELLED = "cancelled"
        REFUNDED = "refunded"
        DELETED = "deleted"

    financial_year = models.ForeignKey("organizations.FinancialYear", on_delete=models.PROTECT, related_name="+")
    event = models.ForeignKey("events.Event", on_delete=models.PROTECT, related_name="payments")
    payer = models.ForeignKey(
        "people.Person",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="payments",
        help_text="Empty for an anonymous (no name) collection",
    )
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
    # When the collectors go back for the money still owed on this pavti (door-to-door follow-up).
    follow_up_on = models.DateField(null=True, blank=True)
    # Answers to the organization's own dropdowns (admin studio): field key -> option picked.
    custom_fields = models.JSONField(default=dict, blank=True)
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
            # ₹0 only when the whole amount was left as a balance (the receipt then shows what is owed).
            models.CheckConstraint(condition=Q(amount__gte=0), name="payment_amount_not_negative"),
        ]
        indexes = [
            models.Index(fields=["organization", "event", "status", "paid_at"], name="payment_org_event_idx"),
            models.Index(fields=["organization", "collector", "paid_at"], name="payment_org_collector_idx"),
            models.Index(fields=["organization", "event", "mode"], name="payment_org_mode_idx"),
            models.Index(fields=["organization", "event", "follow_up_on"], name="payment_org_follow_up_idx"),
        ]

    def __str__(self):
        return f"{self.amount} {self.mode}"

    @property
    def payer_name(self) -> str:
        from django.utils.translation import gettext

        return self.payer.full_name if self.payer_id else gettext("Anonymous")
