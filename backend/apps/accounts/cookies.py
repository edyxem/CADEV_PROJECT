"""Transport du refresh token dans un cookie HttpOnly."""

from django.conf import settings
from rest_framework import exceptions
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.settings import api_settings as jwt_settings


def set_refresh_cookie(response: Response, refresh_token: str) -> None:
    config = settings.AUTH_COOKIE
    response.set_cookie(
        config["NAME"],
        refresh_token,
        max_age=int(jwt_settings.REFRESH_TOKEN_LIFETIME.total_seconds()),
        httponly=True,
        secure=config["SECURE"],
        samesite=config["SAMESITE"],
        domain=config["DOMAIN"] or None,
        path=config["PATH"],
    )


def clear_refresh_cookie(response: Response) -> None:
    config = settings.AUTH_COOKIE
    response.delete_cookie(
        config["NAME"],
        domain=config["DOMAIN"] or None,
        path=config["PATH"],
        samesite=config["SAMESITE"],
    )


def get_refresh_cookie(request: Request) -> str | None:
    return request.COOKIES.get(settings.AUTH_COOKIE["NAME"])


def enforce_trusted_origin(request: Request) -> None:
    """Protège les routes authentifiées par cookie contre les requêtes inter-sites.

    Un navigateur joint toujours l'en-tête ``Origin`` aux POST inter-origines :
    s'il est présent, il doit correspondre à une origine explicitement autorisée.
    """
    origin = request.headers.get("Origin")
    if not origin:
        return
    trusted = {*settings.CORS_ALLOWED_ORIGINS, *settings.CSRF_TRUSTED_ORIGINS}
    trusted.add(f"{request.scheme}://{request.get_host()}")
    if origin not in trusted:
        raise exceptions.PermissionDenied("Origine non autorisée.", code="untrusted_origin")
