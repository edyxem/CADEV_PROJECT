"""Vues transversales."""

from django.db import DatabaseError, connection
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    """Sonde de disponibilité : vérifie l'accès à la base de données."""

    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes: list = []

    @extend_schema(
        tags=["Santé"],
        summary="État du service",
        description="Accès public. Renvoie 503 si la base de données est injoignable.",
        responses={
            200: inline_serializer(
                "HealthResponse",
                {"status": serializers.CharField(), "database": serializers.CharField()},
            ),
        },
    )
    def get(self, request: Request) -> Response:
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except DatabaseError:
            return Response(
                {"status": "degraded", "database": "unavailable"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({"status": "ok", "database": "ok"})
