import tempfile

from .base import *  # noqa: F401,F403
from .base import REST_FRAMEWORK

DEBUG = False
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
SMS_BACKEND = "apps.accounts.sms.MemorySMSBackend"
CELERY_TASK_ALWAYS_EAGER = True
MEDIA_ROOT = tempfile.mkdtemp(prefix="vargani-test-media-")
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
OTP_DEBUG_ECHO = False
REFRESH_COOKIE_SECURE = False
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_THROTTLE_RATES": {"anon": "10000/min", "user": "10000/min", "auth": "10000/min", "otp": "10000/min"},
}
