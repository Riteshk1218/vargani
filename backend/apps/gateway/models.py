from django.db import models

from apps.core.models import TenantModel, TimeStampedModel, UUIDModel

from . import crypto


class GatewayConfig(TenantModel):
    """An organization's own payment gateway account (money goes straight to the organization's bank)."""

    class Provider(models.TextChoices):
        RAZORPAY = "razorpay"

    provider = models.CharField(max_length=20, choices=Provider.choices, default=Provider.RAZORPAY)
    key_id = models.CharField(max_length=100)
    key_secret_encrypted = models.TextField(blank=True)
    webhook_secret_encrypted = models.TextField(blank=True)
    is_active = models.BooleanField(default=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["organization"], name="gateway_one_per_org")]

    @property
    def key_secret(self) -> str:
        return crypto.decrypt(self.key_secret_encrypted)

    @property
    def webhook_secret(self) -> str:
        return crypto.decrypt(self.webhook_secret_encrypted)


class GatewayEvent(UUIDModel, TimeStampedModel):
    """Every webhook delivery, stored once. A replayed event id is acknowledged and ignored."""

    organization = models.ForeignKey(
        "organizations.Organization", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    gateway = models.CharField(max_length=20)
    event_id = models.CharField(max_length=120)
    event_type = models.CharField(max_length=60, blank=True)
    payload = models.JSONField(default=dict)
    signature_valid = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    error = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["gateway", "event_id"], name="gateway_event_unique")]
