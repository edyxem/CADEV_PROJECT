"""Endpoints des profils : annuaire public et gestion de son propre profil."""

from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer
from rest_framework.views import APIView

from common.permissions import is_moderator
from common.schema import errors

from . import selectors, services
from .filters import ProfileFilter
from .models import DeveloperProfile, SocialLink
from .serializers import (
    AvatarSerializer,
    ModerationProfileSerializer,
    OwnerProfileSerializer,
    PublicProfileSerializer,
    RestrictedProfileSerializer,
    SkillInputSerializer,
    SkillSerializer,
    SocialLinkSerializer,
)

TAG = ["Profils"]
ME_TAG = ["Mon profil"]


def _my_profile(request: Request) -> DeveloperProfile:
    return selectors.profiles_with_relations().get(user=request.user)


@extend_schema_view(
    list=extend_schema(
        tags=TAG,
        summary="Annuaire des développeurs",
        description=(
            "Accès public. Seuls les profils publics de comptes actifs apparaissent. Les filtres "
            "`city` et `availability` ignorent les profils qui masquent ces champs."
        ),
    ),
    retrieve=extend_schema(
        tags=TAG,
        summary="Consulter un profil",
        description=(
            "Accès public. Un profil privé renvoie une carte minimale (`is_private=true`) aux "
            "autres membres ; son titulaire et la modération voient le profil complet."
        ),
        responses={200: PublicProfileSerializer, **errors(404)},
    ),
)
class ProfileViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = PublicProfileSerializer
    filterset_class = ProfileFilter
    lookup_field = "username"
    lookup_value_regex = r"[A-Za-z][A-Za-z0-9_]{2,29}"

    def get_queryset(self) -> QuerySet[DeveloperProfile]:
        if self.action == "list":
            return selectors.public_profiles().order_by("-created_at")
        return selectors.profiles_with_relations().filter(user__is_active=True)

    def get_object(self) -> DeveloperProfile:
        return get_object_or_404(
            self.get_queryset(), user__username__iexact=self.kwargs["username"]
        )

    def get_serializer_class(self) -> type[BaseSerializer]:
        if self.action != "retrieve":
            return PublicProfileSerializer
        return self.serializer_class

    def retrieve(self, request: Request, *args, **kwargs) -> Response:
        profile = self.get_object()
        if is_moderator(request.user):
            serializer_class = ModerationProfileSerializer
        elif profile.user_id == request.user.pk:
            serializer_class = OwnerProfileSerializer
        elif not profile.is_public:
            serializer_class = RestrictedProfileSerializer
        else:
            serializer_class = PublicProfileSerializer
        return Response(serializer_class(profile, context={"request": request}).data)


class MyProfileView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=ME_TAG,
        summary="Mon profil",
        description="Réservé au titulaire. Inclut les champs masqués et les réglages.",
        responses={200: OwnerProfileSerializer, **errors(401)},
    )
    def get(self, request: Request) -> Response:
        return Response(
            OwnerProfileSerializer(_my_profile(request), context={"request": request}).data
        )

    @extend_schema(
        tags=ME_TAG,
        summary="Modifier mon profil",
        description=(
            "Pays par code ISO, domaines par slug de catégorie. Le texte est enregistré sans "
            "balise HTML."
        ),
        request=OwnerProfileSerializer,
        responses={200: OwnerProfileSerializer, **errors(400, 401)},
    )
    def patch(self, request: Request) -> Response:
        serializer = OwnerProfileSerializer(
            _my_profile(request), data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            OwnerProfileSerializer(_my_profile(request), context={"request": request}).data
        )


class MySkillsView(APIView):
    permission_classes = [IsAuthenticated]

    def _response(self, request: Request) -> Response:
        skills = request.user.skills.select_related("technology")
        return Response(SkillSerializer(skills, many=True).data)

    @extend_schema(
        tags=ME_TAG,
        summary="Mes compétences",
        responses={200: SkillSerializer(many=True), **errors(401)},
    )
    def get(self, request: Request) -> Response:
        return self._response(request)

    @extend_schema(
        tags=ME_TAG,
        summary="Remplacer mes compétences",
        description=(
            "Remplace la liste complète (30 au maximum). `verification_status` n'est jamais "
            "accepté : il vaut `SELF_DECLARED`, ou `EVIDENCE_ADDED` si une preuve est fournie."
        ),
        request=SkillInputSerializer(many=True),
        responses={200: SkillSerializer(many=True), **errors(400, 401, 409)},
    )
    def put(self, request: Request) -> Response:
        return self._save(request, replace=True)

    @extend_schema(
        tags=ME_TAG,
        summary="Ajouter ou mettre à jour des compétences",
        description="Ne supprime aucune compétence absente de la liste envoyée.",
        request=SkillInputSerializer(many=True),
        responses={200: SkillSerializer(many=True), **errors(400, 401, 409)},
    )
    def patch(self, request: Request) -> Response:
        return self._save(request, replace=False)

    def _save(self, request: Request, *, replace: bool) -> Response:
        serializer = SkillInputSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        services.set_skills(request.user, serializer.validated_data, replace=replace)
        return self._response(request)


@extend_schema_view(
    list=extend_schema(tags=ME_TAG, summary="Mes liens externes"),
    create=extend_schema(
        tags=ME_TAG,
        summary="Ajouter un lien",
        description="URL http/https uniquement, 10 liens au maximum.",
        responses={201: SocialLinkSerializer, **errors(400, 401, 409)},
    ),
    partial_update=extend_schema(tags=ME_TAG, summary="Modifier un lien"),
    destroy=extend_schema(tags=ME_TAG, summary="Supprimer un lien"),
)
class MySocialLinkViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]
    serializer_class = SocialLinkSerializer
    pagination_class = None
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self) -> QuerySet[SocialLink]:
        # Le filtre par titulaire empêche toute modification du lien d'autrui (IDOR → 404).
        return SocialLink.objects.filter(user=self.request.user)

    def perform_create(self, serializer: SocialLinkSerializer) -> None:
        serializer.instance = services.add_social_link(
            self.request.user, **serializer.validated_data
        )

    def create(self, request: Request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class MyAvatarView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    @extend_schema(
        tags=ME_TAG,
        summary="Téléverser mon avatar",
        description=(
            "JPEG, PNG ou WebP, 2 Mo au plus. Le contenu réel est contrôlé, puis l'image est "
            "réencodée en WebP 512 px (métadonnées supprimées)."
        ),
        request={"multipart/form-data": AvatarSerializer},
        responses={200: OwnerProfileSerializer, **errors(400, 401)},
    )
    def put(self, request: Request) -> Response:
        serializer = AvatarSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = services.update_avatar(_my_profile(request), serializer.validated_data["avatar"])
        return Response(OwnerProfileSerializer(profile, context={"request": request}).data)

    @extend_schema(tags=ME_TAG, summary="Supprimer mon avatar", responses={204: None})
    def delete(self, request: Request) -> Response:
        services.remove_avatar(_my_profile(request))
        return Response(status=status.HTTP_204_NO_CONTENT)
