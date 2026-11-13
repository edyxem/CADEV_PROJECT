"""Exceptions métier et format d'erreur uniforme de l'API."""

from typing import Any

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


class BusinessRuleViolation(exceptions.APIException):
    """Action refusée parce qu'elle contredit une règle métier."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "Cette action contredit une règle métier."
    default_code = "business_rule_violation"


class InvalidTransition(BusinessRuleViolation):
    """Changement de statut absent de la table des transitions autorisées."""

    default_detail = "Ce changement de statut n'est pas autorisé."
    default_code = "invalid_transition"


def _as_drf_exception(exc: Exception) -> Exception:
    if isinstance(exc, Http404):
        return exceptions.NotFound()
    if isinstance(exc, DjangoPermissionDenied):
        return exceptions.PermissionDenied()
    if isinstance(exc, DjangoValidationError):
        if hasattr(exc, "message_dict"):
            return exceptions.ValidationError(exc.message_dict)
        return exceptions.ValidationError(exc.messages)
    return exc


def _first_code(codes: Any, fallback: str) -> str:
    """Extrait un code d'erreur lisible d'une structure de codes DRF."""
    if isinstance(codes, str):
        return codes
    if isinstance(codes, list) and codes:
        return _first_code(codes[0], fallback)
    if isinstance(codes, dict) and codes:
        return _first_code(next(iter(codes.values())), fallback)
    return fallback


def api_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    """Renvoie toutes les erreurs sous la forme ``{detail, code, errors}``."""
    exc = _as_drf_exception(exc)
    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    errors: dict[str, Any] = {}
    if isinstance(exc, exceptions.ValidationError):
        detail = "Les données fournies sont invalides."
        code = "validation_error"
        errors = exc.detail if isinstance(exc.detail, dict) else {"non_field_errors": exc.detail}
    elif isinstance(exc, exceptions.APIException):
        detail = str(exc.detail)
        code = _first_code(exc.get_codes(), exc.default_code)
    else:  # pragma: no cover - garde-fou
        detail = "Une erreur est survenue."
        code = "error"

    response.data = {"detail": detail, "code": code, "errors": errors}
    return response
