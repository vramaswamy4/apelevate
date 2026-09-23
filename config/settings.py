"""Settings for APElevate.

All configuration that differs between environments comes from environment variables (or a
local `.env` file in development); see `.env.example` for the full list. Production refuses to
start without a real secret key.
"""

from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env", overwrite=False)

DEBUG = env.bool("DJANGO_DEBUG", default=False)

SECRET_KEY = env("DJANGO_SECRET_KEY", default="")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set when DJANGO_DEBUG is off.")
    SECRET_KEY = "dev-only-insecure-key-never-use-in-production"  # noqa: S105 (DEBUG only)

ALLOWED_HOSTS = env.list(
    "DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "[::1]"] if DEBUG else []
)
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    "django.forms",
    "core",
    "accounts",
    "catalog",
    "classes",
    "payments",
    "planner",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # Secure by default: every view needs a signed-in user unless it's marked
    # @login_not_required. Forgetting a decorator fails closed.
    "django.contrib.auth.middleware.LoginRequiredMiddleware",
    "core.middleware.UserTimezoneMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
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
                "core.context_processors.nav",
            ],
        },
    },
]

FORM_RENDERER = "core.forms.FormRenderer"

WSGI_APPLICATION = "config.wsgi.application"

# SQLite by default so a fresh clone runs with no services; docker-compose and production set
# DATABASE_URL to PostgreSQL.
# An empty DATABASE_URL counts as unset.
DATABASES = {
    "default": env.db_url_config(
        env("DATABASE_URL", default="") or f"sqlite:///{BASE_DIR / 'db.sqlite3'}"
    )
}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DATABASE_CONN_MAX_AGE", default=60)

AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "home"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
        if not DEBUG
        else "django.contrib.staticfiles.storage.StaticFilesStorage"
    },
}

MEDIA_ROOT = env.path("DJANGO_MEDIA_ROOT", default=BASE_DIR / "media")
MEDIA_URL = "media/"
# Mentor CVs and score reports. Outside MEDIA_ROOT and never served by URL.
PRIVATE_MEDIA_ROOT = env.path("DJANGO_PRIVATE_MEDIA_ROOT", default=BASE_DIR / "private_media")
# Production on Cloud Run: a private GCS bucket instead of local disk (see accounts/storage.py).
PRIVATE_STORAGE_BUCKET = env("PRIVATE_STORAGE_BUCKET", default="")
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 12 * 1024 * 1024

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

EMAIL_BACKEND = env(
    "DJANGO_EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend"
    if DEBUG or env.bool("DEMO_MODE", default=False)
    else "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="APElevate <no-reply@apelevate.localhost>")

# Public demo: shows the demo accounts on the sign-in page, lets seed/reset commands run with
# DEBUG off, and stops anyone changing the shared demo accounts' email or password.
DEMO_MODE = env.bool("DEMO_MODE", default=False)
DEMO_EMAIL_DOMAIN = "apelevate.test"

# Payments: "fake" (no network; development and tests) or "paypal".
PAYMENTS_BACKEND = env("PAYMENTS_BACKEND", default="fake" if DEBUG else "paypal")
PAYPAL_CLIENT_ID = env("PAYPAL_CLIENT_ID", default="")
PAYPAL_CLIENT_SECRET = env("PAYPAL_CLIENT_SECRET", default="")
PAYPAL_ENVIRONMENT = env("PAYPAL_ENVIRONMENT", default="sandbox")

# Study-plan model: "fake" (offline, for dev and tests) or "openai" (any OpenAI-compatible API).
# Defaults point at Groq's free tier and an open-weights model; docs/EVALS.md explains the pick.
LLM_BACKEND = env("LLM_BACKEND", default="fake")
LLM_BASE_URL = env("LLM_BASE_URL", default="https://api.groq.com/openai/v1")
LLM_API_KEY = env("LLM_API_KEY", default="")
LLM_MODEL = env("LLM_MODEL", default="openai/gpt-oss-120b")
LLM_REASONING_EFFORT = env("LLM_REASONING_EFFORT", default="low")
PLANNER_DAILY_LIMIT_PER_USER = env.int("PLANNER_DAILY_LIMIT_PER_USER", default=10)
PLANNER_DAILY_TOKEN_BUDGET = env.int("PLANNER_DAILY_TOKEN_BUDGET", default=150_000)

# HTTPS hardening. Off by default so `runserver` works over plain HTTP; production sets
# DJANGO_SECURE=1 behind a TLS-terminating proxy.
SECURE = env.bool("DJANGO_SECURE", default=False)
if SECURE:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = env.int("DJANGO_HSTS_SECONDS", default=60 * 60 * 24 * 30)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = env.bool("DJANGO_HSTS_PRELOAD", default=False)
    if not SECURE_HSTS_PRELOAD:
        # Preloading is close to irreversible for a domain, so it's a deliberate opt-in.
        SILENCED_SYSTEM_CHECKS = ["security.W021"]
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "plain": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"},
    },
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "plain"}},
    "root": {"handlers": ["console"], "level": env("DJANGO_LOG_LEVEL", default="INFO")},
    "loggers": {
        "django.db.backends": {"level": "WARNING"},
    },
}
