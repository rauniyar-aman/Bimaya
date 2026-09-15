"""
Django settings for the Bimaya project.

Environment-driven via django-environ. Copy ``.env.example`` to ``.env`` and
adjust values for your machine. Anything secret or environment-specific lives
in ``.env`` (git-ignored), never in this file.

Docs: https://docs.djangoproject.com/en/6.1/
"""

from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
env = environ.Env(
    DJANGO_DEBUG=(bool, True),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    CORS_ALLOWED_ORIGINS=(list, ["http://localhost:3000", "http://127.0.0.1:3000"]),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY", default="django-insecure-dev-only-change-me")
DEBUG = env.bool("DJANGO_DEBUG", default=True)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:3000")

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
]

LOCAL_APPS = [
    "apps.core",
    "apps.accounts",
    "apps.providers",
    "apps.policies",
    "apps.purchases",
    "apps.payments",
    "apps.documents",
    "apps.claims",
    "apps.leads",
    "apps.notifications",
    "apps.adminpanel",
    "apps.assistant",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "bimaya.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

WSGI_APPLICATION = "bimaya.wsgi.application"
ASGI_APPLICATION = "bimaya.asgi.application"

# ---------------------------------------------------------------------------
# Database (PostgreSQL via DATABASE_URL)
# ---------------------------------------------------------------------------
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://bimaya:bimaya_dev_pw@localhost:5432/bimaya",
    )
}

# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Django REST Framework + JWT + OpenAPI
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 12,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "apps.core.exceptions.api_exception_handler",
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/min",
        "user": "1000/day",
        "otp": "5/min",
        "login": "10/min",
        "ai_chat": "15/min",
        "ai_recommend": "30/min",
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Bimaya API",
    "DESCRIPTION": "Bimaya — digital insurance marketplace for Nepal. REST API.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# ---------------------------------------------------------------------------
# One-time passwords (account verification & password reset)
# ---------------------------------------------------------------------------
OTP_LENGTH = env.int("OTP_LENGTH", default=6)
OTP_EXPIRY_MINUTES = env.int("OTP_EXPIRY_MINUTES", default=10)
OTP_MAX_ATTEMPTS = env.int("OTP_MAX_ATTEMPTS", default=5)

# In development there is no SMS gateway, so the code is returned in the API
# response to keep the signup flow testable. This MUST stay off in production.
OTP_RETURN_IN_RESPONSE = env.bool("OTP_RETURN_IN_RESPONSE", default=DEBUG)

# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------
# In-app + email notifications are always on. SMS is a paid channel, so it is
# off by default and behind a pluggable adapter (apps/notifications/sms.py);
# flip this on and wire a real gateway there to enable it.
NOTIFICATIONS_SMS_ENABLED = env.bool("NOTIFICATIONS_SMS_ENABLED", default=False)

# Web Push (browser notifications) is also off by default. It only activates
# once it is enabled AND a VAPID keypair is configured — see
# apps/notifications/push.py. The private key stays server-side; only the public
# key is safe to ship to the browser (exposed to the frontend as
# NEXT_PUBLIC_VAPID_PUBLIC_KEY). Generate a keypair with:
#   python -c "from py_vapid import Vapid01; v=Vapid01(); v.generate_keys(); \
#     import base64; \
#     print(base64.urlsafe_b64encode(v.public_key.public_bytes(...)))"
# (or `vapid --gen`), then set the three values below in .env.
NOTIFICATIONS_PUSH_ENABLED = env.bool("NOTIFICATIONS_PUSH_ENABLED", default=False)
VAPID_PUBLIC_KEY = env("VAPID_PUBLIC_KEY", default="")
VAPID_PRIVATE_KEY = env("VAPID_PRIVATE_KEY", default="")
# "mailto:" contact the push service can reach you at (VAPID "sub" claim).
VAPID_ADMIN_EMAIL = env("VAPID_ADMIN_EMAIL", default="admin@bimaya.local")

# ---------------------------------------------------------------------------
# AI chat assistant
# ---------------------------------------------------------------------------
# The recommendation engine is rule-based and always on. The free-form chat
# assistant calls an external LLM, so it is off by default and only activates
# once a key is configured (mirrors the SMS flag above). The provider is a seam
# so it can be swapped without touching the app code. No customer PII is ever
# sent to the provider — only the typed question and the public catalogue.
AI_CHAT_ENABLED = env.bool("AI_CHAT_ENABLED", default=False)
AI_CHAT_PROVIDER = env("AI_CHAT_PROVIDER", default="gemini")
GEMINI_API_KEY = env("GEMINI_API_KEY", default="")
GEMINI_MODEL = env("GEMINI_MODEL", default="gemini-flash-latest")

# ---------------------------------------------------------------------------
# Government insurance registry sync (dormant seam)
# ---------------------------------------------------------------------------
# Nepal's insurance regulator may require issued policies to be reported to a
# central registry. That integration is scaffolded but ships OFF: it only runs
# when enabled AND an endpoint and key are configured (see
# apps/adminpanel/gov_integration.py, driven by the `sync_gov_registry`
# management command — never from the request path). Only non-PII regulatory
# metadata is ever sent — policy numbers, plan/provider identifiers and amounts,
# never customer identity, nominee details or KYC.
GOV_INTEGRATION_ENABLED = env.bool("GOV_INTEGRATION_ENABLED", default=False)
GOV_INTEGRATION_ENDPOINT = env("GOV_INTEGRATION_ENDPOINT", default="")
GOV_INTEGRATION_API_KEY = env("GOV_INTEGRATION_API_KEY", default="")

# ---------------------------------------------------------------------------
# CORS (locked to the frontend origin)
# ---------------------------------------------------------------------------
# Both dev hostnames are allowed by default because "localhost" and "127.0.0.1"
# are separate origins to a browser, and the Next.js dev server answers on both.
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=["http://localhost:3000", "http://127.0.0.1:3000"],
)
CORS_ALLOW_CREDENTIALS = True

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kathmandu"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static & media files
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
# Leading slash so uploaded-file URLs are rooted at the host, not the request
# path. Without it, DRF's ``build_absolute_uri`` would join a relative "media/"
# onto whatever endpoint served the record (e.g. ".../auth/media/...").
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Email (Django 6 MAILERS API)
# ---------------------------------------------------------------------------
# Dev ships with the console backend: OTP codes and notification emails print to
# the server log, so signup is testable with zero setup (the code is also echoed
# in the API response — see OTP_RETURN_IN_RESPONSE above). To deliver REAL email,
# set EMAIL_HOST plus the matching credentials in .env — any SMTP provider works
# (Gmail, Brevo, SendGrid, Mailgun, Resend, …). A configured host automatically
# switches the default mailer to SMTP; see .env.example for ready-to-copy blocks.
# (These read into underscore locals, not EMAIL_* settings, because Django 6
# forbids the deprecated EMAIL_* settings once MAILERS is defined.)
_email_backend = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
_email_host = env("EMAIL_HOST", default="")

if _email_host:
    MAILERS = {
        "default": {
            "BACKEND": "django.core.mail.backends.smtp.EmailBackend",
            "OPTIONS": {
                "host": _email_host,
                "port": env.int("EMAIL_PORT", default=587),
                "username": env("EMAIL_HOST_USER", default=""),
                "password": env("EMAIL_HOST_PASSWORD", default=""),
                "use_tls": env.bool("EMAIL_USE_TLS", default=True),
                "use_ssl": env.bool("EMAIL_USE_SSL", default=False),
                "timeout": env.int("EMAIL_TIMEOUT", default=15),
            },
        },
    }
else:
    # No SMTP host → keep the console backend (or whatever EMAIL_BACKEND names,
    # e.g. a file/locmem backend in tests) with no SMTP options attached, so
    # development and CI stay zero-config.
    MAILERS = {"default": {"BACKEND": _email_backend}}

DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="Bimaya <no-reply@bimaya.local>")

# ---------------------------------------------------------------------------
# Payment gateways (sandbox test credentials by default — see
# apps/payments/gateways/ for the sandbox endpoints themselves)
# ---------------------------------------------------------------------------
ESEWA_MERCHANT_CODE = env("ESEWA_MERCHANT_CODE", default="EPAYTEST")
ESEWA_SECRET_KEY = env("ESEWA_SECRET_KEY", default="8gBm/:&EnhH.1/q")
KHALTI_SECRET_KEY = env(
    "KHALTI_SECRET_KEY", default="test_secret_key_68ba473c2ce54774bee9d4791cf34c1c"
)

# ---------------------------------------------------------------------------
# Production hardening (only when DEBUG is off)
# ---------------------------------------------------------------------------
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 365
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
