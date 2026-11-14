from typing import Any

from rest_framework import serializers

from apps.catalog.models import Country, Technology
from apps.catalog.serializers import CountryRefSerializer, TechnologyRefSerializer
from apps.community.serializers import AuthorSerializer
from apps.profiles.serializers import CountryCodeField

from .models import Opportunity, OpportunityInterest, Organization


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["id", "name", "slug", "website", "description", "is_verified", "verified_at"]
        read_only_fields = ["id", "slug", "is_verified", "verified_at"]

    def validate_website(self, value: str) -> str:
        if not value.lower().startswith(("http://", "https://")):
            raise serializers.ValidationError("Seuls les liens http et https sont acceptés.")
        return value


class OrganizationRefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["name", "slug", "is_verified"]


class OpportunitySerializer(serializers.ModelSerializer):
    publisher = AuthorSerializer(read_only=True)
    organization = OrganizationRefSerializer(read_only=True)
    country = CountryRefSerializer(read_only=True)
    technologies = TechnologyRefSerializer(many=True, read_only=True)
    organization_label = serializers.CharField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    is_verified_partner = serializers.SerializerMethodField()

    class Meta:
        model = Opportunity
        fields = [
            "id",
            "type",
            "title",
            "description",
            "organization",
            "organization_label",
            "is_verified_partner",
            "publisher",
            "country",
            "location",
            "work_mode",
            "level",
            "technologies",
            "deadline",
            "is_expired",
            "application_url",
            "contact_email",
            "source_url",
            "status",
            "review_note",
            "published_at",
            "created_at",
        ]
        read_only_fields = fields

    def get_is_verified_partner(self, opportunity: Opportunity) -> bool:
        return bool(opportunity.organization and opportunity.organization.is_verified)

    def to_representation(self, opportunity: Opportunity) -> dict[str, Any]:
        data = super().to_representation(opportunity)
        request = self.context.get("request")
        if not request or request.user.pk != opportunity.publisher_id:
            data.pop("review_note")
        return data


class OpportunityWriteSerializer(serializers.ModelSerializer):
    organization = serializers.SlugRelatedField(
        slug_field="slug", queryset=Organization.objects.all(), required=False, allow_null=True
    )
    country = CountryCodeField(
        slug_field="code",
        queryset=Country.objects.filter(is_active=True),
        required=False,
        allow_null=True,
    )
    technologies = serializers.SlugRelatedField(
        slug_field="slug",
        many=True,
        required=False,
        queryset=Technology.objects.filter(is_active=True),
    )
    submit = serializers.BooleanField(
        default=True,
        write_only=True,
        help_text="false pour un brouillon ; true publie (partenaire vérifié) "
        "ou soumet à validation.",
    )

    class Meta:
        model = Opportunity
        fields = [
            "type",
            "title",
            "description",
            "organization",
            "organization_name",
            "country",
            "location",
            "work_mode",
            "level",
            "technologies",
            "deadline",
            "application_url",
            "contact_email",
            "source_url",
            "submit",
        ]
        extra_kwargs = {"source_url": {"required": True}}

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        for field in ("application_url", "source_url"):
            url = attrs.get(field, "")
            if url and not url.lower().startswith(("http://", "https://")):
                raise serializers.ValidationError(
                    {field: ["Seuls les liens http et https sont acceptés."]}
                )
        if (
            self.instance is None
            and not attrs.get("organization")
            and not attrs.get("organization_name", "").strip()
        ):
            raise serializers.ValidationError(
                {"organization_name": ["Indiquez l'organisation qui publie l'offre."]}
            )
        return attrs


class ReviewSerializer(serializers.Serializer):
    approve = serializers.BooleanField()
    note = serializers.CharField(required=False, allow_blank=True, max_length=500)


class InterestSerializer(serializers.ModelSerializer):
    user = AuthorSerializer(read_only=True)

    class Meta:
        model = OpportunityInterest
        fields = ["id", "user", "kind", "message", "created_at"]
        read_only_fields = ["id", "user", "created_at"]


class VerifySerializer(serializers.Serializer):
    verified = serializers.BooleanField(default=True)
