from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex, OpClass
from django.db import models
from django.db.models import Q
from django.db.models.functions import Upper

from apps.core.models import SoftDeleteModel, SoftDeleteQuerySet, TenantModel


class PersonType(models.TextChoices):
    MEMBER = "member", "Member"
    KARYAKARTA = "karyakarta", "Karyakarta"
    VOLUNTEER = "volunteer", "Volunteer"
    DONOR = "donor", "Donor"
    SUPPORTER = "supporter", "Supporter"
    OTHER = "other", "Other"


class Person(TenantModel, SoftDeleteModel):
    """Someone who belongs to an organization. A login account (User) is optional and separate."""

    full_name = models.CharField(max_length=150)
    mobile = models.CharField(max_length=16, blank=True)
    alt_mobile = models.CharField(max_length=16, blank=True)
    email = models.EmailField(blank=True)
    unit = models.CharField(max_length=50, blank=True, help_text="Flat / house number")
    building = models.CharField(max_length=100, blank=True, help_text="Building / wing")
    area = models.CharField(max_length=100, blank=True)
    address_line = models.CharField(max_length=250, blank=True)
    city = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
    person_types = ArrayField(models.CharField(max_length=20, choices=PersonType.choices), default=list, blank=True)
    notes = models.TextField(blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="people"
    )
    is_active = models.BooleanField(default=True)

    objects = SoftDeleteQuerySet.as_manager()

    class Meta:
        ordering = ["full_name"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "id"], name="person_org_id_unique"),
            models.UniqueConstraint(
                fields=["organization", "user"], condition=Q(user__isnull=False), name="person_one_per_user_per_org"
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "mobile"], name="person_org_mobile_idx"),
            models.Index(fields=["organization", "full_name"], name="person_org_name_idx"),
            GinIndex(OpClass(Upper("full_name"), name="gin_trgm_ops"), name="person_name_trgm_idx"),
            GinIndex(fields=["person_types"], name="person_types_gin_idx"),
        ]

    def __str__(self):
        return self.full_name
