from django.db import models
from django.db.models import F, Q

from apps.core.models import TenantModel


class ContributionType(TenantModel):
    """What people contribute towards inside one event, e.g. "Monthly Vargani" or "Annual Donation".

    Amounts are always flexible. `suggested_min/max` only guide the collector. When `is_mandatory` is set,
    `target_amount` is the amount expected from each event participant (per month for recurring types),
    which drives the outstanding view.
    """

    class Kind(models.TextChoices):
        ONE_TIME = "one_time"
        RECURRING_MONTHLY = "recurring_monthly"

    event = models.ForeignKey("events.Event", on_delete=models.PROTECT, related_name="contribution_types")
    fund = models.ForeignKey(
        "funds.Fund", null=True, blank=True, on_delete=models.PROTECT, related_name="contribution_types"
    )
    name = models.CharField(max_length=120)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.ONE_TIME)
    suggested_min = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    suggested_max = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    target_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    is_mandatory = models.BooleanField(default=False)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    # Lists and the Collect dropdown show lower positions first; the default types come first, Donation leading.
    position = models.PositiveSmallIntegerField(default=100)

    class Meta:
        ordering = ["position", "name"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "id"], name="ctype_org_id_unique"),
            models.UniqueConstraint(fields=["event", "id"], name="ctype_event_id_unique"),
            models.UniqueConstraint(fields=["event", "name"], name="ctype_event_name_unique"),
            models.CheckConstraint(
                condition=Q(suggested_min__isnull=True)
                | Q(suggested_max__isnull=True)
                | Q(suggested_min__lte=F("suggested_max")),
                name="ctype_suggested_range",
            ),
            models.CheckConstraint(
                condition=Q(target_amount__isnull=True) | Q(target_amount__gt=0), name="ctype_target_positive"
            ),
            models.CheckConstraint(
                condition=Q(is_mandatory=False) | Q(target_amount__isnull=False), name="ctype_mandatory_has_target"
            ),
        ]

    def __str__(self):
        return self.name


class Contribution(TenantModel):
    """One line of money towards one contribution type (and month, for recurring types).

    A payment settles one or more lines, so ₹1,000 covering two months is one payment with two lines, and
    ₹300 + ₹200 in the same month are two payments with one line each.
    """

    class Status(models.TextChoices):
        PENDING = "pending"
        CONFIRMED = "confirmed"
        CANCELLED = "cancelled"
        REFUNDED = "refunded"

    financial_year = models.ForeignKey("organizations.FinancialYear", on_delete=models.PROTECT, related_name="+")
    event = models.ForeignKey("events.Event", on_delete=models.PROTECT, related_name="contributions")
    fund = models.ForeignKey("funds.Fund", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    contribution_type = models.ForeignKey(ContributionType, on_delete=models.PROTECT, related_name="contributions")
    person = models.ForeignKey(
        "people.Person", null=True, blank=True, on_delete=models.PROTECT, related_name="contributions"
    )  # empty for an anonymous collection
    payment = models.ForeignKey("payments.Payment", on_delete=models.PROTECT, related_name="lines")
    period_month = models.DateField(null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    contributed_on = models.DateField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.CONFIRMED)
    collector = models.ForeignKey(
        "organizations.OrganizationMembership", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    notes = models.CharField(max_length=300, blank=True)
    # Set when this line pays (part of) an earlier balance.
    due = models.ForeignKey("Due", null=True, blank=True, on_delete=models.PROTECT, related_name="settlements")

    class Meta:
        ordering = ["-contributed_on", "-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "id"], name="contribution_org_id_unique"),
            models.CheckConstraint(condition=Q(amount__gt=0), name="contribution_amount_positive"),
            models.CheckConstraint(
                condition=Q(period_month__isnull=True) | Q(period_month__day=1), name="contribution_period_first_day"
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "event", "status", "contributed_on"], name="contrib_org_event_idx"),
            models.Index(fields=["organization", "event", "person"], name="contrib_org_person_idx"),
            models.Index(fields=["organization", "event", "period_month"], name="contrib_org_period_idx"),
            models.Index(fields=["organization", "collector", "contributed_on"], name="contrib_org_collector_idx"),
        ]


class Due(TenantModel):
    """A balance (baaki): money a person still owes for a contribution, recorded when the receipt was given
    but not all of the money came. It is paid off by later contribution lines that point to it, so what is
    still owed is `amount` minus their confirmed total and never stored twice.

    Only confirmed money counts as collected; a balance never adds to income until it is paid.
    """

    class Status(models.TextChoices):
        OPEN = "open"
        CANCELLED = "cancelled"  # written off, or its receipt was voided

    financial_year = models.ForeignKey("organizations.FinancialYear", on_delete=models.PROTECT, related_name="+")
    event = models.ForeignKey("events.Event", on_delete=models.PROTECT, related_name="dues")
    contribution_type = models.ForeignKey(ContributionType, on_delete=models.PROTECT, related_name="dues")
    person = models.ForeignKey("people.Person", on_delete=models.PROTECT, related_name="dues")
    # The collection whose receipt shows this balance.
    payment = models.ForeignKey("payments.Payment", on_delete=models.PROTECT, related_name="dues")
    period_month = models.DateField(null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    collector = models.ForeignKey(
        "organizations.OrganizationMembership", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    status_reason = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "id"], name="due_org_id_unique"),
            models.CheckConstraint(condition=Q(amount__gt=0), name="due_amount_positive"),
            models.CheckConstraint(
                condition=Q(period_month__isnull=True) | Q(period_month__day=1), name="due_period_first_day"
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "event", "status"], name="due_org_event_idx"),
            models.Index(fields=["organization", "person"], name="due_org_person_idx"),
        ]


class CollectorAssignment(TenantModel):
    """Which collector (karyakarta) collects from which person in an event. Ended, never deleted."""

    event = models.ForeignKey("events.Event", on_delete=models.PROTECT, related_name="collector_assignments")
    collector = models.ForeignKey(
        "organizations.OrganizationMembership", on_delete=models.PROTECT, related_name="assignments"
    )
    person = models.ForeignKey("people.Person", on_delete=models.PROTECT, related_name="collector_assignments")
    assigned_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    active_from = models.DateTimeField(auto_now_add=True)
    active_to = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["person__full_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["event", "person"], condition=Q(is_active=True), name="assignment_one_active_per_person"
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "event", "collector", "is_active"], name="assign_collector_idx")
        ]
