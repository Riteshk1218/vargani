from django.conf import settings
from django.db import models

from apps.core.models import TenantModel


class ExportJob(TenantModel):
    """A report file being built in the background. Only the user who asked can download it."""

    class Format(models.TextChoices):
        CSV = "csv"
        XLSX = "xlsx"
        PDF = "pdf"

    class Status(models.TextChoices):
        PENDING = "pending"
        RUNNING = "running"
        DONE = "done"
        FAILED = "failed"

    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    membership = models.ForeignKey("organizations.OrganizationMembership", on_delete=models.PROTECT, related_name="+")
    report_type = models.CharField(max_length=40)
    format = models.CharField(max_length=4, choices=Format.choices)
    filters = models.JSONField(default=dict, blank=True)
    language = models.CharField(max_length=8, default="en")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    file = models.CharField(max_length=300, blank=True)
    file_name = models.CharField(max_length=200, blank=True)
    row_count = models.PositiveIntegerField(null=True, blank=True)
    error = models.CharField(max_length=300, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["organization", "requested_by", "created_at"], name="export_org_user_idx")]
