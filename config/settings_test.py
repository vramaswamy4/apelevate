"""Settings for the test suite: deterministic whatever is in a developer's .env."""

import os
import tempfile

os.environ["DJANGO_DEBUG"] = "0"
os.environ["DJANGO_SECURE"] = "0"
os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-secret-key")

from .settings import *  # noqa: F403

ALLOWED_HOSTS = ["testserver", "localhost"]
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]  # fast; tests only
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
MEDIA_ROOT = tempfile.mkdtemp(prefix="apelevate-media-")
STATIC_ROOT = tempfile.mkdtemp(prefix="apelevate-static-")
PRIVATE_MEDIA_ROOT = tempfile.mkdtemp(prefix="apelevate-private-")
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
PAYMENTS_BACKEND = "fake"
PAYPAL_CLIENT_ID = ""
PAYPAL_CLIENT_SECRET = ""
LOGGING["root"]["level"] = "WARNING"  # noqa: F405
