from django.conf import settings as django_settings
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateRangeField, RangeOperators
from django.db import models
from django.db.models import F, Func, Q

from apps.core.models import TenantModel, TimeStampedModel, UUIDModel


class Organization(UUIDModel, TimeStampedModel):
    class Status(models.TextChoices):
        ACTIVE = "active"
        SUSPENDED = "suspended"
        CLOSED = "closed"

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=80, unique=True)
    logo = models.CharField(max_length=300, blank=True)  # storage key, e.g. orgs/<id>/logo/<uuid>.png
    address_line1 = models.CharField(max_length=200, blank=True)
    address_line2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
    country = models.CharField(max_length=60, default="India")
    phone = models.CharField(max_length=16, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    description = models.TextField(blank=True)
    registration_type = models.CharField(max_length=60, blank=True)
    registration_number = models.CharField(max_length=60, blank=True)
    default_language = models.CharField(max_length=8, default="en")
    receipt_language = models.CharField(max_length=8, default="en")
    currency = models.CharField(max_length=3, default="INR")
    timezone = models.CharField(max_length=64, default="Asia/Kolkata")
    settings = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)
    created_by = models.ForeignKey(
        django_settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name="+"
    )

    def __str__(self):
        return self.name


class FinancialYear(TenantModel):
    class Status(models.TextChoices):
        OPEN = "open"
        CLOSED = "closed"

    label = models.CharField(max_length=20)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    is_current = models.BooleanField(default=False)

    class Meta:
        ordering = ["-start_date"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "id"], name="fy_org_id_unique"),
            models.UniqueConstraint(fields=["organization", "label"], name="fy_org_label_unique"),
            models.UniqueConstraint(fields=["organization"], condition=Q(is_current=True), name="fy_one_current"),
            models.CheckConstraint(condition=Q(end_date__gt=F("start_date")), name="fy_end_after_start"),
            ExclusionConstraint(
                name="fy_no_overlap",
                expressions=[
                    ("organization", RangeOperators.EQUAL),
                    (
                        Func(
                            F("start_date"),
                            F("end_date"),
                            models.Value("[]"),
                            function="daterange",
                            output_field=DateRangeField(),
                        ),
                        RangeOperators.OVERLAPS,
                    ),
                ],
            ),
        ]

    def __str__(self):
        return self.label


class Permission(models.Model):
    code = models.CharField(max_length=80, unique=True)
    module = models.CharField(max_length=40)
    description = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["module", "code"]

    def __str__(self):
        return self.code


class Role(UUIDModel, TimeStampedModel):
    organization = models.ForeignKey(
        Organization, null=True, blank=True, on_delete=models.PROTECT, related_name="roles"
    )  # NULL = system role
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=300, blank=True)
    is_system = models.BooleanField(default=False)
    rank = models.PositiveSmallIntegerField(default=100)  # display order
    permissions = models.ManyToManyField(Permission, through="RolePermission", related_name="roles")

    class Meta:
        ordering = ["rank", "name"]
        constraints = [
            models.UniqueConstraint(fields=["code"], condition=Q(organization__isnull=True), name="role_system_code"),
            models.UniqueConstraint(fields=["organization", "code"], name="role_org_code"),
        ]

    def __str__(self):
        return self.name


class RolePermission(models.Model):
    class Scope(models.TextChoices):
        ALL = "all"
        OWN = "own"
        ASSIGNED = "assigned"
        SELF = "self"
        FINANCIAL = "financial"  # audit log: financial entities only

    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="role_permissions")
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name="+")
    scope = models.CharField(max_length=10, choices=Scope.choices, default=Scope.ALL)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["role", "permission"], name="role_permission_unique")]

    def __str__(self):
        return f"{self.role_id}:{self.permission_id}:{self.scope}"


class OrganizationMembership(UUIDModel, TimeStampedModel):
    class Status(models.TextChoices):
        ACTIVE = "active"
        SUSPENDED = "suspended"
        REMOVED = "removed"

    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="memberships")
    user = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="memberships")
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="memberships")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)
    joined_at = models.DateTimeField(auto_now_add=True)
    invited_by = models.ForeignKey(
        django_settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )

    class Meta:
        ordering = ["joined_at"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "user"], name="membership_org_user_unique"),
            models.UniqueConstraint(fields=["organization", "id"], name="membership_org_id_unique"),
        ]
        indexes = [models.Index(fields=["user", "status"], name="membership_user_status_idx")]


class Invitation(TenantModel):
    class Status(models.TextChoices):
        PENDING = "pending"
        ACCEPTED = "accepted"
        REVOKED = "revoked"
        EXPIRED = "expired"

    email = models.EmailField(null=True, blank=True)
    mobile = models.CharField(max_length=16, null=True, blank=True)
    full_name = models.CharField(max_length=150, blank=True)
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="+")
    token_hash = models.CharField(max_length=64, unique=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    expires_at = models.DateTimeField()
    accepted_by = models.ForeignKey(
        django_settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(email__isnull=False) | Q(mobile__isnull=False), name="invitation_has_destination"
            ),
        ]
