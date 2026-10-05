from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models


class AuditLog(models.Model):
    """Append-only record of who did what. UPDATE and DELETE are blocked by a database trigger."""

    id = models.BigAutoField(primary_key=True)
    organization = models.ForeignKey(
        "organizations.Organization", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    actor_membership_id = models.UUIDField(null=True, blank=True)
    actor_role_code = models.CharField(max_length=50, blank=True)
    action = models.CharField(max_length=40)
    entity_type = models.CharField(max_length=80)
    entity_id = models.CharField(max_length=64, blank=True)
    before = models.JSONField(null=True, blank=True)
    after = models.JSONField(null=True, blank=True)
    changed_fields = ArrayField(models.CharField(max_length=80), default=list, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    device_id = models.CharField(max_length=100, blank=True)
    request_id = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["organization", "-created_at"], name="audit_org_created_idx"),
            models.Index(fields=["organization", "entity_type", "entity_id"], name="audit_org_entity_idx"),
            models.Index(fields=["actor_user", "-created_at"], name="audit_actor_created_idx"),
        ]

    def __str__(self):
        return f"{self.action} {self.entity_type}:{self.entity_id}"
