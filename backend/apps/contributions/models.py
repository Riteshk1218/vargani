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

    class Meta:
        ordering = ["name"]
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
    person = models.ForeignKey("people.Person", on_delete=models.PROTECT, related_name="contributions")
    payment = models.ForeignKey("payments.Payment", on_delete=models.PROTECT, related_name="lines")
    period_month = models.DateField(null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    contributed_on = models.DateField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.CONFIRMED)
    collector = models.ForeignKey(
        "organizations.OrganizationMembership", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    notes = models.CharField(max_length=300, blank=True)

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
