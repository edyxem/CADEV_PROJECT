"""Briques OpenAPI partagées : format d'erreur et réponses standard."""

from drf_spectacular.utils import OpenApiResponse
from rest_framework import serializers


class ErrorSerializer(serializers.Serializer):
    """Format unique des erreurs de l'API."""

    detail = serializers.CharField()
    code = serializers.CharField()
    errors = serializers.DictField(child=serializers.ListField(child=serializers.CharField()))


ERROR_DESCRIPTIONS = {
    400: "Données invalides (`validation_error`).",
    401: "Authentification requise ou jeton invalide.",
    403: "Permission insuffisante pour cette action.",
    404: "Ressource introuvable ou non visible.",
    409: "Règle métier ou transition de statut non respectée.",
    429: "Trop de requêtes : limite de débit atteinte.",
}


def errors(*status_codes: int) -> dict[int, OpenApiResponse]:
    """Construit les réponses d'erreur documentées d'un endpoint."""
    return {
        code: OpenApiResponse(ErrorSerializer, description=ERROR_DESCRIPTIONS[code])
        for code in status_codes
    }
