import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

E164 = re.compile(r"^\+[1-9]\d{7,14}$")


def normalize_mobile(value: str | None, default_country_code: str = "91") -> str | None:
    """Normalise a mobile number to E.164. Ten-digit Indian numbers get +91."""
    if value is None:
        return None
    raw = re.sub(r"[\s\-().]", "", str(value))
    if not raw:
        return None
    if raw.startswith("00"):
        raw = "+" + raw[2:]
    if not raw.startswith("+"):
        if len(raw) == 11 and raw.startswith("0"):
            raw = raw[1:]
        if len(raw) == 10:
            raw = f"+{default_country_code}{raw}"
        else:
            raw = "+" + raw
    if not E164.match(raw):
        raise ValidationError(_("Enter a valid mobile number."), code="invalid_mobile")
    return raw
