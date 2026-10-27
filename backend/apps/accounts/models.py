import re

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.ids import uuid7
from apps.core.phone import normalize_mobile


class Language(models.TextChoices):
    ENGLISH = "en", "English"
    MARATHI = "mr", "मराठी"
    HINDI = "hi", "हिन्दी"


class ThemeColor(models.TextChoices):
    """The app's main color. The website and the mobile app map each name to their own shades."""

    ORANGE = "orange", "Orange"
    RED = "red", "Red"
    MAROON = "maroon", "Maroon"
    PINK = "pink", "Pink"
    PURPLE = "purple", "Purple"
    INDIGO = "indigo", "Indigo"
    BLUE = "blue", "Blue"
    TEAL = "teal", "Teal"
    GREEN = "green", "Green"


# A username starts with a letter, so it can never be mistaken for a mobile number or an email at login.
USERNAME_PATTERN = re.compile(r"^[a-z][a-z0-9._-]{2,29}$")


def normalize_username(value: str) -> str:
    """Lower-case and check a login username such as "ramesh.p". Raises ValidationError."""
    value = (value or "").strip().lower()
    if not USERNAME_PATTERN.match(value):
        raise ValidationError(
            _("A username has 3 to 30 letters, numbers, dots, dashes or underscores and starts with a letter."),
            code="invalid_username",
        )
    return value


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, full_name, email=None, mobile=None, password=None, username=None, **extra):
        email = self.normalize_email(email).lower() if email else None
        mobile = normalize_mobile(mobile) if mobile else None
        username = normalize_username(username) if username else None
        if not email and not mobile and not username:
            raise ValueError("A user needs an email, a mobile number or a username.")
        user = self.model(full_name=full_name, email=email, mobile=mobile, username=username, **extra)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_user(self, full_name, email=None, mobile=None, password=None, username=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_user(full_name, email, mobile, password, username, **extra)

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
    # Set by an organization admin for people who log in without an email or mobile number (lower case).
    username = models.CharField(max_length=30, null=True, blank=True, unique=True)
    preferred_language = models.CharField(max_length=8, choices=Language.choices, default=Language.ENGLISH)
    # The user's own app color; empty means the organization's color.
    theme_color = models.CharField(max_length=16, choices=ThemeColor.choices, blank=True, default="")
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
                condition=models.Q(email__isnull=False)
                | models.Q(mobile__isnull=False)
                | models.Q(username__isnull=False),
                name="user_has_login_identifier",
            ),
            models.UniqueConstraint(Lower("email"), name="user_email_ci_unique"),
        ]

    def __str__(self):
        return self.full_name

    @property
    def is_verified(self):
        if self.email_verified_at or self.mobile_verified_at:
            return True
        # A username-only login is made by an admin who vouches for it; there is nothing to send a code to.
        return bool(self.username and not self.email and not self.mobile)


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
