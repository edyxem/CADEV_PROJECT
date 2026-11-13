"""Réglages de la suite de tests."""

from .base import *  # noqa: F403
from .base import AUTH_COOKIE, REST_FRAMEWORK, ROOT_DIR, STORAGES

DEBUG = False
SECRET_KEY = "test-only-insecure-secret-key"
ALLOWED_HOSTS = ["testserver", "localhost"]

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
MEDIA_ROOT = ROOT_DIR / ".test_media"
STORAGES["staticfiles"] = {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}

CORS_ALLOWED_ORIGINS = ["http://localhost:3000"]
CSRF_TRUSTED_ORIGINS = ["http://localhost:3000"]
AUTH_COOKIE["SECURE"] = False

# Limites volontairement très hautes : les tests de throttling les surchargent.
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = dict.fromkeys(
    REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"], "100000/min"
)
