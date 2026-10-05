from django.db import models
from django.db.models import F, Q

from apps.core.models import SoftDeleteModel, SoftDeleteQuerySet, TenantModel


class EventTemplate(models.TextChoices):
    FESTIVAL = "festival"
    FUNDRAISING = "fundraising"
    MEMBERSHIP = "membership"
    SOCIETY = "society"
    CUSTOM = "custom"


class Event(TenantModel, SoftDeleteModel):
    """An isolated workspace (e.g. "Ganesh Chaturthi 2027"). Financial data always belongs to one event."""

    class Status(models.TextChoices):
        DRAFT = "draft"
        ACTIVE = "active"
        CLOSED = "closed"
        ARCHIVED = "archived"

    financial_year = models.ForeignKey("organizations.FinancialYear", on_delete=models.PROTECT, related_name="events")
    name = models.CharField(max_length=150)
    template = models.CharField(max_length=20, choices=EventTemplate.choices, default=EventTemplate.CUSTOM)
    code = models.CharField(max_length=12, help_text="Receipt prefix, e.g. GC")
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    modules = models.JSONField(default=dict, blank=True)
    target_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    description = models.TextField(blank=True)
    thank_you_message = models.CharField(max_length=300, blank=True)

    objects = SoftDeleteQuerySet.as_manager()

    class Meta:
        ordering = ["-start_date", "name"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "id"], name="event_org_id_unique"),
            models.UniqueConstraint(fields=["id", "financial_year"], name="event_id_fy_unique"),
            models.UniqueConstraint(fields=["organization", "financial_year", "code"], name="event_fy_code_unique"),
            models.CheckConstraint(
                condition=Q(target_amount__isnull=True) | Q(target_amount__gt=0), name="event_target_positive"
            ),
            models.CheckConstraint(
                condition=Q(start_date__isnull=True) | Q(end_date__isnull=True) | Q(end_date__gte=F("start_date")),
                name="event_end_after_start",
            ),
        ]
        indexes = [models.Index(fields=["organization", "status"], name="event_org_status_idx")]

    def __str__(self):
        return self.name


class EventParticipant(TenantModel):
    class Role(models.TextChoices):
        PARTICIPANT = "participant"
        VOLUNTEER = "volunteer"
        KARYAKARTA = "karyakarta"
        GUEST = "guest"

    class Status(models.TextChoices):
        ACTIVE = "active"
        INACTIVE = "inactive"

    event = models.ForeignKey(Event, on_delete=models.PROTECT, related_name="participants")
    person = models.ForeignKey("people.Person", on_delete=models.PROTECT, related_name="event_participations")
    participation_role = models.CharField(max_length=20, choices=Role.choices, default=Role.PARTICIPANT)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    notes = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["created_at"]
        constraints = [models.UniqueConstraint(fields=["event", "person"], name="participant_event_person_unique")]
