from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.core.models import TenantModel
from apps.payments.models import PaymentMode


class ExpenseCategory(TenantModel):
    """What money is spent on. Seeded per organization; names are the organization's own data."""

    name = models.CharField(max_length=80)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "id"], name="expcat_org_id_unique"),
            models.UniqueConstraint(fields=["organization", "name"], name="expcat_org_name_unique"),
        ]

    def __str__(self):
        return self.name


class Expense(TenantModel):
    """Money spent for an event. Only approved expenses count in the balance. Never deleted: voided instead."""

    class Status(models.TextChoices):
        DRAFT = "draft"
        SUBMITTED = "submitted"
        APPROVED = "approved"
        REJECTED = "rejected"
        VOID = "void"

    financial_year = models.ForeignKey("organizations.FinancialYear", on_delete=models.PROTECT, related_name="+")
    event = models.ForeignKey("events.Event", on_delete=models.PROTECT, related_name="expenses")
    category = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT, related_name="expenses")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    expense_date = models.DateField()
    mode = models.CharField(max_length=20, choices=PaymentMode.choices, default=PaymentMode.CASH)
    payee = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    reference_number = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.CharField(max_length=300, blank=True)
    void_reason = models.CharField(max_length=300, blank=True)
    voided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    voided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-expense_date", "-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "id"], name="expense_org_id_unique"),
            models.CheckConstraint(condition=Q(amount__gt=0), name="expense_amount_positive"),
        ]
        indexes = [
            models.Index(fields=["organization", "event", "status", "expense_date"], name="expense_org_event_idx"),
        ]


class ExpenseAttachment(TenantModel):
    """A bill or photo for an expense. The file is validated by its content, not its name."""

    expense = models.ForeignKey(Expense, on_delete=models.PROTECT, related_name="attachments")
    file = models.CharField(max_length=300)
    original_name = models.CharField(max_length=200)
    content_type = models.CharField(max_length=60)
    size_bytes = models.PositiveIntegerField()

    class Meta:
        ordering = ["created_at"]


class OtherIncome(TenantModel):
    """Income not from a person: donation box (hundi), sponsorship, bank interest, sales."""

    class Source(models.TextChoices):
        DONATION_BOX = "donation_box"
        SPONSORSHIP = "sponsorship"
        INTEREST = "interest"
        SALE = "sale"
        OTHER = "other"

    class Status(models.TextChoices):
        RECORDED = "recorded"
        VOID = "void"

    financial_year = models.ForeignKey("organizations.FinancialYear", on_delete=models.PROTECT, related_name="+")
    event = models.ForeignKey("events.Event", on_delete=models.PROTECT, related_name="other_income")
    fund = models.ForeignKey("funds.Fund", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    source = models.CharField(max_length=20, choices=Source.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    received_on = models.DateField()
    mode = models.CharField(max_length=20, choices=PaymentMode.choices, default=PaymentMode.CASH)
    reference_number = models.CharField(max_length=100, blank=True)
    description = models.CharField(max_length=300, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.RECORDED)
    void_reason = models.CharField(max_length=300, blank=True)
    voided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    voided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-received_on", "-created_at"]
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name="other_income_amount_positive"),
        ]
        indexes = [
            models.Index(fields=["organization", "event", "status", "received_on"], name="income_org_event_idx"),
        ]
