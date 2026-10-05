from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

from apps.core.ids import uuid7
from apps.core.phone import normalize_mobile


class Language(models.TextChoices):
    ENGLISH = "en", "English"
    MARATHI = "mr", "मराठी"
    HINDI = "hi", "हिन्दी"


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, full_name, email=None, mobile=None, password=None, **extra):
        email = self.normalize_email(email).lower() if email else None
        mobile = normalize_mobile(mobile) if mobile else None
        if not email and not mobile:
            raise ValueError("A user needs an email or a mobile number.")
        user = self.model(full_name=full_name, email=email, mobile=mobile, **extra)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_user(self, full_name, email=None, mobile=None, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_user(full_name, email, mobile, password, **extra)

    def create_superuser(self, email, password, full_name="Platform Admin", **extra):
        extra.update(is_staff=True, is_superuser=True, is_platform_admin=True)
        user = self._create_user(full_name, email=email, password=password, **extra)
        user.email_verified_at = timezone.now()
        user.save(update_fields=["email_verified_at"])
        return user


class User(AbstractBaseUser, PermissionsMixin):
    """A login identity. Organization data access comes only from OrganizationMembership."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    full_name = models.CharField(max_length=150)
    email = models.EmailField(null=True, blank=True, unique=True)
    mobile = models.CharField(max_length=16, null=True, blank=True, unique=True)
    preferred_language = models.CharField(max_length=8, choices=Language.choices, default=Language.ENGLISH)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    mobile_verified_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)  # Django admin access (platform operations only)
    is_platform_admin = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(email__isnull=False) | models.Q(mobile__isnull=False),
                name="user_has_email_or_mobile",
            ),
            models.UniqueConstraint(Lower("email"), name="user_email_ci_unique"),
        ]

    def __str__(self):
        return self.full_name

    @property
    def is_verified(self):
        return bool(self.email_verified_at or self.mobile_verified_at)


class OTPChallenge(models.Model):
    class Purpose(models.TextChoices):
        REGISTER = "register"
        LOGIN = "login"
        VERIFY = "verify"
        RESET = "reset"

    class Channel(models.TextChoices):
        EMAIL = "email"
        SMS = "sms"

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    purpose = models.CharField(max_length=20, choices=Purpose.choices)
    channel = models.CharField(max_length=10, choices=Channel.choices)
    destination = models.CharField(max_length=254)
    code_hash = models.CharField(max_length=128)
    attempts = models.PositiveSmallIntegerField(default=0)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["destination", "purpose", "created_at"], name="otp_dest_purpose_idx")]

    def __str__(self):
        return f"{self.purpose} OTP for {self.destination}"
