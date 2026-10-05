from django.db import models
from django.db.models import Q

from apps.core.models import TenantModel


class Fund(TenantModel):
    """A pot of money inside one event (e.g. "Pandal Fund", "Annadan"). Archive with is_active=False."""

    event = models.ForeignKey("events.Event", on_delete=models.PROTECT, related_name="funds")
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    target_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "id"], name="fund_org_id_unique"),
            models.UniqueConstraint(fields=["event", "id"], name="fund_event_id_unique"),
            models.UniqueConstraint(fields=["event", "name"], name="fund_event_name_unique"),
            models.CheckConstraint(
                condition=Q(target_amount__isnull=True) | Q(target_amount__gt=0), name="fund_target_positive"
            ),
        ]

    def __str__(self):
        return self.name
