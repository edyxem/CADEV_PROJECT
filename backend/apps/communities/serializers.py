from rest_framework import serializers

from apps.catalog.models import Category, Country, Technology
from apps.catalog.serializers import (
    CategoryRefSerializer,
    CountryRefSerializer,
    TechnologyRefSerializer,
)
from apps.community.serializers import AuthorSerializer
from apps.profiles.serializers import CountryCodeField

from . import services
from .models import Community, CommunityMembership


class CommunitySerializer(serializers.ModelSerializer):
    country = CountryRefSerializer(read_only=True)
    technology = TechnologyRefSerializer(read_only=True)
    category = CategoryRefSerializer(read_only=True)
    member_count = serializers.IntegerField(read_only=True, default=0)
    my_role = serializers.SerializerMethodField()

    class Meta:
        model = Community
        fields = [
            "id",
            "name",
            "slug",
            "kind",
            "description",
            "rules",
            "country",
            "city",
            "technology",
            "category",
            "member_count",
            "my_role",
            "created_at",
        ]
        read_only_fields = fields

    def get_my_role(self, community: Community) -> str | None:
        request = self.context.get("request")
        member = services.membership(community, request.user) if request else None
        return member.role if member else None


class CommunityWriteSerializer(serializers.ModelSerializer):
    country = CountryCodeField(
        slug_field="code",
        queryset=Country.objects.filter(is_active=True),
        required=False,
        allow_null=True,
    )
    technology = serializers.SlugRelatedField(
        slug_field="slug",
        queryset=Technology.objects.filter(is_active=True),
        required=False,
        allow_null=True,
    )
    category = serializers.SlugRelatedField(
        slug_field="slug",
        queryset=Category.objects.filter(is_active=True),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Community
        fields = [
            "name",
            "kind",
            "description",
            "rules",
            "country",
            "city",
            "technology",
            "category",
        ]


class MembershipSerializer(serializers.ModelSerializer):
    user = AuthorSerializer(read_only=True)

    class Meta:
        model = CommunityMembership
        fields = ["id", "user", "role", "status", "created_at"]
        read_only_fields = fields


class MembershipUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=CommunityMembership.Role.choices, required=False)
    ban = serializers.BooleanField(default=False)


class LocalModerationSerializer(serializers.Serializer):
    hidden = serializers.BooleanField(default=True)
    reason = serializers.CharField(min_length=5, max_length=500)
