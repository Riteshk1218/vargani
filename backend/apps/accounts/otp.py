import hashlib
import hmac
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework.exceptions import Throttled, ValidationError

from .models import OTPChallenge
from .sms import sms_enabled
from .tasks import deliver_otp


def _hash(destination: str, purpose: str, code: str) -> str:
    message = f"{destination}|{purpose}|{code}".encode()
    return hmac.new(settings.SECRET_KEY.encode(), message, hashlib.sha256).hexdigest()


def channel_for(destination: str) -> str:
    return OTPChallenge.Channel.EMAIL if "@" in destination else OTPChallenge.Channel.SMS


def issue_otp(destination: str, purpose: str, ip: str | None = None) -> str:
    """Create and send a one-time code. Returns the code (callers only expose it in debug mode)."""
    if channel_for(destination) == OTPChallenge.Channel.SMS and not sms_enabled():
        message = _("Login codes by SMS are not switched on yet. Use your email address.")
        raise ValidationError({"detail": message}, code="sms_disabled")
    now = timezone.now()
    recent = OTPChallenge.objects.filter(destination=destination, purpose=purpose)
    last = recent.order_by("-created_at").first()
    if last and (now - last.created_at).total_seconds() < settings.OTP_RESEND_COOLDOWN_SECONDS:
        wait = settings.OTP_RESEND_COOLDOWN_SECONDS - int((now - last.created_at).total_seconds())
        raise Throttled(wait=wait, detail=_("Please wait before requesting another code."))
    if recent.filter(created_at__gte=now - timedelta(hours=1)).count() >= settings.OTP_MAX_SENDS_PER_HOUR:
        raise Throttled(detail=_("Too many codes requested. Try again later."))

    code = "".join(secrets.choice("0123456789") for _ in range(settings.OTP_LENGTH))
    channel = channel_for(destination)
    OTPChallenge.objects.create(
        purpose=purpose,
        channel=channel,
        destination=destination,
        code_hash=_hash(destination, purpose, code),
        expires_at=now + timedelta(seconds=settings.OTP_TTL_SECONDS),
        ip=ip,
    )
    minutes = settings.OTP_TTL_SECONDS // 60
    message = _("Your verification code is %(code)s. It expires in %(minutes)s minutes. Do not share it.") % {
        "code": code,
        "minutes": minutes,
    }
    transaction.on_commit(lambda: deliver_otp.delay(channel, destination, _("Your verification code"), message))
    return code


def verify_otp(destination: str, purpose: str, code: str) -> None:
    """Consume a valid code or raise ValidationError. Wrong codes count toward the attempt limit.

    Must not run inside an outer transaction, so failed attempts are persisted before raising.
    """
    verified = False
    with transaction.atomic():
        challenge = (
            OTPChallenge.objects.select_for_update()
            .filter(destination=destination, purpose=purpose, consumed_at__isnull=True)
            .order_by("-created_at")
            .first()
        )
        usable = (
            challenge is not None
            and challenge.expires_at >= timezone.now()
            and challenge.attempts < settings.OTP_MAX_ATTEMPTS
        )
        if usable:
            if hmac.compare_digest(challenge.code_hash, _hash(destination, purpose, str(code).strip())):
                challenge.consumed_at = timezone.now()
                challenge.save(update_fields=["consumed_at"])
                verified = True
            else:
                challenge.attempts += 1
                challenge.save(update_fields=["attempts"])
    if not verified:
        raise ValidationError({"code": [_("The code is invalid or has expired.")]}, code="invalid_otp")
