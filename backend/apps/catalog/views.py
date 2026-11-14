"""Endpoints des référentiels : lecture publique, écriture administrateur."""

from django.db.models import QuerySet
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.request import Request
from rest_framework.response import Response

from common.permissions import IsAdminOrReadOnly, is_admin
from common.schema import errors

from .models import Category, Country, Tag, Technology
from .serializers import CategorySerializer, CountrySerializer, TagSerializer, TechnologySerializer

SEARCH_PARAM = OpenApiParameter("search", str, description="Recherche dans le nom.")
WRITE_DOC = "Réservé aux administrateurs."


def reference_schema(tag: str, label: str) -> dict:
    return {
        "list": extend_schema(
            tags=[tag],
            summary=f"Lister les {label}",
            description="Accès public. Les éléments désactivés ne sont visibles que des admins.",
            parameters=[SEARCH_PARAM],
        ),
        "retrieve": extend_schema(tags=[tag], summary="Détail", responses={404: None}),
        "create": extend_schema(
            tags=[tag],
            summary="Créer",
            description=WRITE_DOC,
            responses={201: None, **errors(400, 401, 403)},
        ),
        "partial_update": extend_schema(
            tags=[tag], summary="Modifier", description=WRITE_DOC, responses=errors(400, 401, 403)
        ),
        "update": extend_schema(
            tags=[tag], summary="Remplacer", description=WRITE_DOC, responses=errors(400, 401, 403)
        ),
        "destroy": extend_schema(
            tags=[tag],
            summary="Désactiver",
            description=(
                f"{WRITE_DOC} Désactivation logique : l'historique des contenus liés est conservé."
            ),
            responses={204: None, **errors(401, 403)},
        ),
    }


class ReferenceViewSet(viewsets.ModelViewSet):
    """Base commune : lecture ouverte, écriture admin, désactivation au lieu de suppression."""

    permission_classes = [IsAdminOrReadOnly]
    lookup_field = "slug"
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self) -> QuerySet:
        queryset = self.queryset.all()
        if not is_admin(self.request.user):
            queryset = queryset.filter(is_active=True)
        search = self.request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(name__icontains=search)
        return queryset

    def destroy(self, request: Request, *args, **kwargs) -> Response:
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(**reference_schema("Référentiels", "catégories"))
class CategoryViewSet(ReferenceViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


@extend_schema_view(**reference_schema("Référentiels", "tags"))
class TagViewSet(ReferenceViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer


@extend_schema_view(**reference_schema("Référentiels", "technologies"))
class TechnologyViewSet(ReferenceViewSet):
    queryset = Technology.objects.select_related("category")
    serializer_class = TechnologySerializer


@extend_schema_view(**reference_schema("Référentiels", "pays"))
class CountryViewSet(ReferenceViewSet):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    lookup_field = "code"
    lookup_value_regex = "[A-Za-z]{2}"

    def get_object(self) -> Country:
        self.kwargs["code"] = self.kwargs["code"].upper()
        return super().get_object()
