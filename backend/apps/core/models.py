from django.conf import settings
from django.db import models
from django.utils import timezone

from .ids import uuid7


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)

    class Meta:
        abstract = True


class TenantQuerySet(models.QuerySet):
    def for_org(self, organization):
        if organization is None:
            return self.none()
        return self.filter(organization=organization)


class TenantModel(UUIDModel, TimeStampedModel):
    """Base for every organization-owned table. organization_id is always stored directly on the row."""

    organization = models.ForeignKey("organizations.Organization", on_delete=models.PROTECT, related_name="+")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )

    objects = TenantQuerySet.as_manager()

    class Meta:
        abstract = True


class SoftDeleteQuerySet(TenantQuerySet):
    def alive(self):
        return self.filter(deleted_at__isnull=True)


class SoftDeleteModel(models.Model):
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def soft_delete(self, user=None):
        self.deleted_at = timezone.now()
        update_fields = ["deleted_at", "updated_at"]
        if hasattr(self, "is_active"):
            self.is_active = False
            update_fields.append("is_active")
        if user is not None and hasattr(self, "updated_by"):
            self.updated_by = user
            update_fields.append("updated_by")
        self.save(update_fields=update_fields)


class StoredFile(models.Model):
    """An uploaded file kept in PostgreSQL (STORAGE_BACKEND=database). Not tenant-scoped itself: files are only
    reachable through the records that point at them, and the API checks those."""

    name = models.CharField(max_length=500, unique=True)
    content = models.BinaryField()
    size = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
