from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel, UUIDModel


class Notification(UUIDModel, TimeStampedModel):
    """One message to one user. The text is rendered from `type` + `params` in the reader's language, so the
    same row reads correctly in English, Marathi and Hindi (see templates.py)."""

    class Channel(models.TextChoices):
        IN_APP = "in_app"
        PUSH = "push"
        SMS = "sms"
        EMAIL = "email"

    class Status(models.TextChoices):
        QUEUED = "queued"
        SENT = "sent"
        FAILED = "failed"
        READ = "read"

    organization = models.ForeignKey(
        "organizations.Organization", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    type = models.CharField(max_length=40)
    params = models.JSONField(default=dict, blank=True)
    channel = models.CharField(max_length=10, choices=Channel.choices, default=Channel.IN_APP)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.SENT)
    entity_type = models.CharField(max_length=80, blank=True)
    entity_id = models.CharField(max_length=64, blank=True)
    link = models.CharField(max_length=200, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "read_at", "created_at"], name="notif_recipient_idx"),
            models.Index(fields=["organization", "type", "entity_id"], name="notif_org_type_idx"),
        ]


class DeviceToken(UUIDModel, TimeStampedModel):
    """A phone (or browser) that receives push notifications for a user. Registered by the mobile app after
    login and removed on logout. A token belongs to one user at a time: a shared phone that logs in as someone
    else moves the token to the new user."""

    class Platform(models.TextChoices):
        ANDROID = "android"
        IOS = "ios"
        WEB = "web"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="devices")
    token = models.CharField(max_length=512, unique=True)
    platform = models.CharField(max_length=10, choices=Platform.choices, default=Platform.ANDROID)
    app_version = models.CharField(max_length=40, blank=True)
    is_active = models.BooleanField(default=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    failure_count = models.PositiveSmallIntegerField(default=0)

    class Meta:
        indexes = [models.Index(fields=["user", "is_active"], name="device_user_active_idx")]
