"""Production settings. Every secret comes from the environment; startup fails if a required one is missing."""

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403
from .base import LOGGING, MIDDLEWARE, env

DEBUG = False
OTP_DEBUG_ECHO = False
REFRESH_COOKIE_SECURE = True

if not env("FIELD_ENCRYPTION_KEY", default=""):
    raise ImproperlyConfigured("Set FIELD_ENCRYPTION_KEY (see backend/.env.example) before starting in production.")
if env("SMS_BACKEND", default="").endswith("ConsoleSMSBackend") and not env.bool("ALLOW_CONSOLE_SMS", default=False):
    raise ImproperlyConfigured("SMS_BACKEND is the console backend: members would never receive login codes.")

# HTTPS everywhere. The reverse proxy terminates TLS and sets X-Forwarded-Proto.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
SECURE_REDIRECT_EXEMPT = [r"^api/v1/health/"]  # load balancer checks over plain HTTP inside the network
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=False)  # opt in once the whole domain is HTTPS
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = "DENY"

MIDDLEWARE = [*MIDDLEWARE, "apps.core.security.SecurityHeadersMiddleware"]

# Database: keep connections open between requests; check them before use.
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True  # noqa: F405

# Structured JSON logs on stdout (collected by Docker / systemd / the hosting platform).
LOGGING = {
    **LOGGING,
    "formatters": {**LOGGING["formatters"], "json": {"()": "apps.core.logging.JSONFormatter"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": env("LOG_FORMAT", default="json")}},
    "loggers": {
        **LOGGING["loggers"],
        "django.security": {"level": "WARNING"},
        "django.db.backends": {"level": "WARNING"},
    },
}

# Optional error tracking. Install `sentry-sdk` and set SENTRY_DSN to switch it on.
SENTRY_DSN = env("SENTRY_DSN", default="")
if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.django import DjangoIntegration
    except ImportError as exc:  # pragma: no cover - depends on deployment
        raise ImproperlyConfigured(
            "SENTRY_DSN is set but sentry-sdk is not installed (pip install sentry-sdk)."
        ) from exc
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration(), CeleryIntegration()],
        environment=env("SENTRY_ENVIRONMENT", default="production"),
        release=env("APP_VERSION", default=None),
        traces_sample_rate=env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.0),
        send_default_pii=False,  # never send names, mobiles or amounts to a third party
    )
