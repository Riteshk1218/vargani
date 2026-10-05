from django.db import models
from django.db.models import Q

from apps.core.models import TenantModel


class ReceiptSeries(TenantModel):
    """Counter behind receipt numbers such as GC-2027-00001. Locked with SELECT ... FOR UPDATE when used."""

    event = models.ForeignKey("events.Event", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    prefix = models.CharField(max_length=12)
    year_label = models.CharField(max_length=10)
    padding = models.PositiveSmallIntegerField(default=5)
    next_number = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["organization", "id"], name="series_org_id_unique"),
            models.UniqueConstraint(fields=["organization", "prefix", "year_label"], name="series_org_prefix_year"),
        ]

    def format(self, number: int) -> str:
        return f"{self.prefix}-{self.year_label}-{number:0{self.padding}d}"


class Receipt(TenantModel):
    """Issued in the same transaction as the successful payment. Its snapshot never changes afterwards."""

    class Status(models.TextChoices):
        ISSUED = "issued"
        VOID = "void"

    financial_year = models.ForeignKey("organizations.FinancialYear", on_delete=models.PROTECT, related_name="+")
    event = models.ForeignKey("events.Event", on_delete=models.PROTECT, related_name="receipts")
    payment = models.ForeignKey("payments.Payment", on_delete=models.PROTECT, related_name="receipts")
    series = models.ForeignKey(ReceiptSeries, on_delete=models.PROTECT, related_name="receipts")
    sequence = models.PositiveIntegerField()
    receipt_number = models.CharField(max_length=40)
    issued_at = models.DateTimeField()
    language = models.CharField(max_length=5, default="en")
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.ISSUED)
    void_reason = models.CharField(max_length=300, blank=True)
    voided_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    voided_at = models.DateTimeField(null=True, blank=True)
    replaces_receipt = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="replaced_by"
    )
    snapshot = models.JSONField()

    class Meta:
        ordering = ["-issued_at", "-sequence"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "id"], name="receipt_org_id_unique"),
            models.UniqueConstraint(fields=["series", "sequence"], name="receipt_series_sequence_unique"),
            models.UniqueConstraint(fields=["organization", "receipt_number"], name="receipt_org_number_unique"),
            models.UniqueConstraint(
                fields=["payment"], condition=Q(status="issued"), name="receipt_one_issued_per_payment"
            ),
            models.UniqueConstraint(
                fields=["replaces_receipt"],
                condition=Q(replaces_receipt__isnull=False),
                name="receipt_corrected_once",
            ),
        ]
        indexes = [models.Index(fields=["organization", "event", "issued_at"], name="receipt_org_event_idx")]

    def __str__(self):
        return self.receipt_number


class ReceiptShare(TenantModel):
    """A public, expiring link to one receipt (used for WhatsApp). Only the token hash is stored."""

    receipt = models.ForeignKey(Receipt, on_delete=models.PROTECT, related_name="shares")
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    view_count = models.PositiveIntegerField(default=0)


class ReceiptVoidRequest(TenantModel):
    """Request to void (and optionally correct) a receipt. Approval voids the receipt and cancels the payment."""

    class Status(models.TextChoices):
        PENDING = "pending"
        APPROVED = "approved"
        REJECTED = "rejected"

    receipt = models.ForeignKey(Receipt, on_delete=models.PROTECT, related_name="void_requests")
    requested_by = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="+")
    reason = models.CharField(max_length=300)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    decided_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["receipt"], condition=Q(status="pending"), name="void_request_one_pending_per_receipt"
            ),
        ]
