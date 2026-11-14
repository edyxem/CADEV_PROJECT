"""Sérialiseurs séparés selon le lecteur : public, restreint, propriétaire, modération."""

from typing import Any

from rest_framework import serializers

from apps.catalog.models import Category, Country, Technology
from apps.catalog.serializers import (
    CategoryRefSerializer,
    CountryRefSerializer,
    TechnologyRefSerializer,
)
from common.sanitization import to_plain_text

from .models import DeveloperProfile, Language, SocialLink, UserSkill


class SkillSerializer(serializers.ModelSerializer):
    technology = TechnologyRefSerializer(read_only=True)
    verification_label = serializers.CharField(
        source="get_verification_status_display", read_only=True
    )
    is_verified = serializers.SerializerMethodField(
        help_text="Vrai uniquement après validation par des pairs ; un lien ne suffit pas."
    )

    class Meta:
        model = UserSkill
        fields = [
            "id",
            "technology",
            "level",
            "years_experience",
            "verification_status",
            "verification_label",
            "is_verified",
            "evidence_url",
        ]
        read_only_fields = fields

    def get_is_verified(self, skill: UserSkill) -> bool:
        return skill.verification_status == UserSkill.VerificationStatus.PEER_REVIEWED


class SkillInputSerializer(serializers.Serializer):
    technology = serializers.SlugRelatedField(
        slug_field="slug", queryset=Technology.objects.filter(is_active=True)
    )
    level = serializers.ChoiceField(choices=UserSkill._meta.get_field("level").choices)
    years_experience = serializers.IntegerField(
        min_value=0, max_value=60, required=False, allow_null=True
    )
    evidence_url = serializers.URLField(required=False, allow_blank=True, max_length=200)

    def validate_evidence_url(self, value: str) -> str:
        if value and not value.lower().startswith(("http://", "https://")):
            raise serializers.ValidationError("Seuls les liens http et https sont acceptés.")
        return value


class PublicLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocialLink
        fields = ["id", "platform", "url"]


class SocialLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocialLink
        fields = ["id", "platform", "url", "is_public", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_url(self, value: str) -> str:
        if not value.lower().startswith(("http://", "https://")):
            raise serializers.ValidationError("Seuls les liens http et https sont acceptés.")
        return value


class RestrictedProfileSerializer(serializers.ModelSerializer):
    """Carte minimale d'un profil privé : aucune donnée au-delà de l'identité publique."""

    username = serializers.CharField(source="user.username", read_only=True)
    is_private = serializers.SerializerMethodField()

    class Meta:
        model = DeveloperProfile
        fields = ["username", "display_name", "avatar", "is_private"]
        read_only_fields = fields

    def get_is_private(self, profile: DeveloperProfile) -> bool:
        return not profile.is_public


class PublicProfileSerializer(serializers.ModelSerializer):
    """Profil public : ne contient ni e-mail, ni champ masqué, ni lien privé."""

    username = serializers.CharField(source="user.username", read_only=True)
    member_since = serializers.DateTimeField(source="user.date_joined", read_only=True)
    country = CountryRefSerializer(read_only=True)
    domains = CategoryRefSerializer(many=True, read_only=True)
    skills = SkillSerializer(source="user.skills", many=True, read_only=True)
    links = serializers.SerializerMethodField()
    is_private = serializers.SerializerMethodField()

    class Meta:
        model = DeveloperProfile
        fields = [
            "username",
            "display_name",
            "headline",
            "bio",
            "avatar",
            "country",
            "city",
            "languages",
            "experience_level",
            "availability_status",
            "domains",
            "skills",
            "links",
            "member_since",
            "is_private",
        ]
        read_only_fields = fields

    def get_links(self, profile: DeveloperProfile) -> list[dict[str, Any]]:
        links = getattr(profile.user, "public_links", None)
        if links is None:
            links = profile.user.social_links.filter(is_public=True)
        return PublicLinkSerializer(links, many=True).data

    def get_is_private(self, profile: DeveloperProfile) -> bool:
        return not profile.is_public

    def to_representation(self, profile: DeveloperProfile) -> dict[str, Any]:
        data = super().to_representation(profile)
        if not profile.show_city:
            data["city"] = None
        if not profile.show_availability:
            data["availability_status"] = None
        return data


class CountryCodeField(serializers.SlugRelatedField):
    """Code pays ISO accepté quelle que soit la casse (« ci » → « CI »)."""

    def to_internal_value(self, data: Any) -> Country:
        return super().to_internal_value(str(data).strip().upper())


class OwnerProfileSerializer(PublicProfileSerializer):
    """Vue du titulaire : tous ses champs et ses réglages de visibilité."""

    country = CountryCodeField(
        slug_field="code",
        queryset=Country.objects.filter(is_active=True),
        required=False,
        allow_null=True,
    )
    domains = serializers.SlugRelatedField(
        slug_field="slug",
        many=True,
        queryset=Category.objects.filter(is_active=True),
        required=False,
    )
    languages = serializers.ListField(
        child=serializers.ChoiceField(choices=Language.choices), required=False, max_length=8
    )
    links = SocialLinkSerializer(source="user.social_links", many=True, read_only=True)

    class Meta(PublicProfileSerializer.Meta):
        fields = [
            *PublicProfileSerializer.Meta.fields,
            "profile_visibility",
            "show_city",
            "show_availability",
            "updated_at",
        ]
        read_only_fields = ["username", "avatar", "skills", "links", "member_since", "updated_at"]

    def validate_display_name(self, value: str) -> str:
        value = to_plain_text(value)
        if not value:
            raise serializers.ValidationError("Le nom d'affichage est obligatoire.")
        return value

    def validate_headline(self, value: str) -> str:
        return to_plain_text(value)

    def validate_bio(self, value: str) -> str:
        return to_plain_text(value)

    def validate_city(self, value: str) -> str:
        return to_plain_text(value)

    def validate_languages(self, value: list[str]) -> list[str]:
        return list(dict.fromkeys(value))

    def to_representation(self, profile: DeveloperProfile) -> dict[str, Any]:
        # Le titulaire voit ses propres champs masqués.
        return serializers.ModelSerializer.to_representation(self, profile)


class ModerationProfileSerializer(OwnerProfileSerializer):
    """Vue modération : ajoute l'état du compte, jamais le mot de passe."""

    email = serializers.EmailField(source="user.email", read_only=True)
    role = serializers.CharField(source="user.role", read_only=True)
    is_active = serializers.BooleanField(source="user.is_active", read_only=True)

    class Meta(OwnerProfileSerializer.Meta):
        fields = [*OwnerProfileSerializer.Meta.fields, "email", "role", "is_active"]
        read_only_fields = fields


class AvatarSerializer(serializers.Serializer):
    avatar = serializers.ImageField()
