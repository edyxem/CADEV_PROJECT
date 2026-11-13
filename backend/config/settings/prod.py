"""Réglages de production (et de démonstration déployée)."""

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403
from .base import ALLOWED_HOSTS, LOGGING, SECRET_KEY, env

DEBUG = False

if not SECRET_KEY:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY est obligatoire en production.")
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS est obligatoire en production.")

# HTTPS ---------------------------------------------------------------------
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = env.int("DJANGO_SECURE_HSTS_SECONDS", default=31536000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# Cookies -------------------------------------------------------------------
SESSION_COOKIE_SECURE = env.bool("DJANGO_COOKIE_SECURE", default=True)
CSRF_COOKIE_SECURE = env.bool("DJANGO_COOKIE_SECURE", default=True)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"

# Journaux JSON, sans données sensibles --------------------------------------
LOGGING["handlers"]["console"]["formatter"] = "json"
