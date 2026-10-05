"""Encrypt gateway secrets at rest (Fernet: AES-128-CBC + HMAC-SHA256).

Set FIELD_ENCRYPTION_KEY (a Fernet key) in production. Without it, a key is derived from SECRET_KEY, which
is fine for development but means rotating SECRET_KEY makes stored secrets unreadable.
"""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


def _fernet() -> Fernet:
    key = getattr(settings, "FIELD_ENCRYPTION_KEY", "") or base64.urlsafe_b64encode(
        hashlib.sha256(("vargani-fields:" + settings.SECRET_KEY).encode()).digest()
    )
    return Fernet(key)


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode() if value else ""


def decrypt(value: str) -> str:
    if not value:
        return ""
    try:
        return _fernet().decrypt(value.encode()).decode()
    except InvalidToken:
        return ""
