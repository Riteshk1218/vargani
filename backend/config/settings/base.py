"""Base settings shared by every environment. All secrets come from the environment."""

import os
from datetime import timedelta
from pathlib import Path

import environ
from celery.schedules import crontab
from django.utils.translation import gettext_lazy as _

from config import dburl

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env", overwrite=False)

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    # third party
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    "drf_spectacular",
    "corsheaders",
    # local
    "apps.core",
    "apps.accounts",
    "apps.audit",
    "apps.organizations",
    "apps.people",
    "apps.events",
    "apps.funds",
    "apps.contributions",
    "apps.payments",
    "apps.receipts",
    "apps.expenses",
    "apps.reports",
    "apps.notifications",
    "apps.portal",
    "apps.gateway",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.core.middleware.RequestIDMiddleware",
    "apps.core.rls.TenantDatabaseMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# DATABASE_URL, or only DATABASE_ADMIN_URL on hosted Postgres (see config/dburl.py).
DATABASE_ADMIN_URL = env("DATABASE_ADMIN_URL", default="")
APP_DB_ROLE = env("APP_DB_ROLE", default=dburl.APP_ROLE_DEFAULT)
if not env("DATABASE_URL", default="") and DATABASE_ADMIN_URL:
    os.environ["DATABASE_URL"] = dburl.app_url(DATABASE_ADMIN_URL, APP_DB_ROLE, SECRET_KEY)
DATABASES = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["ATOMIC_REQUESTS"] = False
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=60)

AUTH_USER_MODEL = "accounts.User"

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- i18n -------------------------------------------------------------------
LANGUAGE_CODE = "en"
LANGUAGES = [("en", _("English")), ("mr", "मराठी"), ("hi", "हिन्दी")]
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# --- static & media ---------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = env("MEDIA_URL", default="/media/")
MEDIA_ROOT = Path(env("MEDIA_ROOT", default=str(BASE_DIR / "media")))

# Local filesystem in development; S3-compatible object storage (S3 / R2 / Supabase) in production;
# "database" keeps files in PostgreSQL (free hosting without a persistent disk, see docs/deploy/RENDER.md).
STORAGE_BACKEND = env("STORAGE_BACKEND", default="local")
if STORAGE_BACKEND == "s3":
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": {
                "bucket_name": env("STORAGE_BUCKET"),
                "endpoint_url": env("STORAGE_ENDPOINT_URL", default=None),
                "region_name": env("STORAGE_REGION", default=None),
                "access_key": env("STORAGE_ACCESS_KEY"),
                "secret_key": env("STORAGE_SECRET_KEY"),
                "default_acl": "private",
                "querystring_auth": True,
                "querystring_expire": 3600,
                "file_overwrite": False,
            },
        },
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
elif STORAGE_BACKEND == "database":
    STORAGES = {
        "default": {"BACKEND": "apps.core.storage.DatabaseStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
else:
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }

DATA_UPLOAD_MAX_MEMORY_SIZE = 12 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
LOGO_MAX_BYTES = 5 * 1024 * 1024

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- DRF --------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework_simplejwt.authentication.JWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.StandardPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "apps.core.exceptions.api_exception_handler",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": env("THROTTLE_ANON", default="60/min"),
        "user": env("THROTTLE_USER", default="600/min"),
        "auth": env("THROTTLE_AUTH", default="10/min"),
        "otp": env("THROTTLE_OTP", default="5/min"),
        "public_receipt": env("THROTTLE_PUBLIC_RECEIPT", default="30/min"),
        "reports": env("THROTTLE_REPORTS", default="60/min"),
        "exports": env("THROTTLE_EXPORTS", default="10/min"),
    },
    "COERCE_DECIMAL_TO_STRING": True,
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env.int("JWT_ACCESS_MINUTES", default=15)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env.int("JWT_REFRESH_DAYS", default=30)),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "SIGNING_KEY": env("JWT_SIGNING_KEY", default=SECRET_KEY),
}

# Web clients keep the refresh token in an HttpOnly cookie scoped to the auth endpoints.
REFRESH_COOKIE_NAME = "vargani_refresh"
REFRESH_COOKIE_PATH = "/api/v1/auth/"
REFRESH_COOKIE_SECURE = env.bool("REFRESH_COOKIE_SECURE", default=True)

SPECTACULAR_SETTINGS = {
    "TITLE": "Vargani Platform API",
    "DESCRIPTION": "Multi-tenant contribution management API for web and mobile clients.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": r"/api/v1",
}

# --- CORS -------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOW_CREDENTIALS = True
from corsheaders.defaults import default_headers  # noqa: E402

CORS_ALLOW_HEADERS = (*default_headers, "x-organization-id", "x-client-type", "idempotency-key", "accept-language")
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

# --- Cache / Celery ---------------------------------------------------------
REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")
CACHES = {"default": {"BACKEND": "django.core.cache.backends.redis.RedisCache", "LOCATION": REDIS_URL}}
if env("CACHE_BACKEND", default="redis") == "locmem":  # one small server without Redis
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=False)
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_TIMEZONE = "UTC"
CELERY_BEAT_SCHEDULE = {
    "monthly-dues-reminders": {
        "task": "apps.portal.tasks.send_monthly_reminders",
        # 5th of each month, 04:30 UTC (10:00 IST)
        "schedule": crontab(minute=30, hour=4, day_of_month=5),
    },
}

# --- Email / OTP ------------------------------------------------------------
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="no-reply@localhost")

SMS_BACKEND = env("SMS_BACKEND", default="apps.accounts.sms.ConsoleSMSBackend")
SMS_MSG91_AUTH_KEY = env("SMS_MSG91_AUTH_KEY", default="")
SMS_MSG91_TEMPLATE_ID = env("SMS_MSG91_TEMPLATE_ID", default="")
SMS_TWILIO_ACCOUNT_SID = env("SMS_TWILIO_ACCOUNT_SID", default="")
SMS_TWILIO_AUTH_TOKEN = env("SMS_TWILIO_AUTH_TOKEN", default="")
SMS_TWILIO_FROM = env("SMS_TWILIO_FROM", default="")
# Push notifications to the mobile app: "console" (logs only) or "fcm" (Firebase Cloud Messaging HTTP v1).
PUSH_BACKEND = env("PUSH_BACKEND", default="console")
FCM_SERVICE_ACCOUNT_FILE = env("FCM_SERVICE_ACCOUNT_FILE", default="")
FCM_PROJECT_ID = env("FCM_PROJECT_ID", default="")
OTP_LENGTH = 6
OTP_TTL_SECONDS = 300
OTP_MAX_ATTEMPTS = 5
OTP_RESEND_COOLDOWN_SECONDS = 30
OTP_MAX_SENDS_PER_HOUR = 5
# Development convenience only: include the OTP in API responses. Forced off in prod settings.
OTP_DEBUG_ECHO = env.bool("OTP_DEBUG_ECHO", default=False)

INVITATION_TTL_DAYS = 7
FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:5173")
API_PUBLIC_URL = env("API_PUBLIC_URL", default="http://localhost:8000")

# Render sets RENDER_EXTERNAL_HOSTNAME (e.g. vargani.onrender.com): website and API share that address.
RENDER_EXTERNAL_HOSTNAME = env("RENDER_EXTERNAL_HOSTNAME", default="")
if RENDER_EXTERNAL_HOSTNAME:
    _origin = f"https://{RENDER_EXTERNAL_HOSTNAME}"
    ALLOWED_HOSTS = [*ALLOWED_HOSTS, RENDER_EXTERNAL_HOSTNAME]
    CSRF_TRUSTED_ORIGINS = [*CSRF_TRUSTED_ORIGINS, _origin]
    CORS_ALLOWED_ORIGINS = [*CORS_ALLOWED_ORIGINS, _origin]
    FRONTEND_URL = env("FRONTEND_URL", default=_origin)
    API_PUBLIC_URL = env("API_PUBLIC_URL", default=_origin)

# The built React website, when Django serves it itself (one service, no nginx). Empty: nginx serves it.
WEBSITE_DIR = env("WEBSITE_DIR", default="")
if WEBSITE_DIR:
    MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
    WHITENOISE_ROOT = WEBSITE_DIR
    WHITENOISE_IMMUTABLE_FILE_TEST = r"^/assets/"  # Vite puts a content hash in every file name there
# Encrypts payment gateway secrets at rest. Empty means a key derived from SECRET_KEY (development only).
FIELD_ENCRYPTION_KEY = env("FIELD_ENCRYPTION_KEY", default="")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"plain": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "plain"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
    # PDF rendering libraries are very chatty at INFO/DEBUG.
    "loggers": {name: {"level": "WARNING"} for name in ("fontTools", "weasyprint")},
}
REQUIRE_VERIFIED_LOGIN = True

SPECTACULAR_SETTINGS["ENUM_NAME_OVERRIDES"] = {
    "LanguageEnum": "apps.accounts.models.Language",
    "PaymentStatusEnum": "apps.payments.models.Payment.Status",
    "ContributionStatusEnum": "apps.contributions.models.Contribution.Status",
    "ReceiptStatusEnum": "apps.receipts.models.Receipt.Status",
    "NewPaymentStatusEnum": ["successful", "pending"],
    "PaymentModeEnum": "apps.payments.models.PaymentMode",
    "ManualPaymentModeEnum": ["cash", "upi", "bank_transfer", "cheque", "other"],
    "OrganizationStatusEnum": "apps.organizations.models.Organization.Status",
}
