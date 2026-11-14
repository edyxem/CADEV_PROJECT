from typing import Any

from rest_framework import serializers

from apps.accounts.models import User
from apps.catalog.models import Category, Technology
from apps.catalog.serializers import CategoryRefSerializer, TechnologyRefSerializer
from apps.community.serializers import AuthorSerializer

from .models import Follow

LOOKUPS = {
    Follow.TargetType.USER: (User.objects.filter(is_active=True), "username__iexact"),
    Follow.TargetType.TECHNOLOGY: (Technology.objects.filter(is_active=True), "slug"),
    Follow.TargetType.CATEGORY: (Category.objects.filter(is_active=True), "slug"),
}


class FollowSerializer(serializers.ModelSerializer):
    followed_user = AuthorSerializer(read_only=True)
    technology = TechnologyRefSerializer(read_only=True)
    category = CategoryRefSerializer(read_only=True)

    class Meta:
        model = Follow
        fields = ["id", "target_type", "followed_user", "technology", "category", "created_at"]
        read_only_fields = fields


class FollowCreateSerializer(serializers.Serializer):
    target_type = serializers.ChoiceField(choices=Follow.TargetType.choices)
    target = serializers.CharField(
        max_length=90, help_text="Nom d'utilisateur, ou slug de technologie / catégorie."
    )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        queryset, lookup = LOOKUPS[attrs["target_type"]]
        target = queryset.filter(**{lookup: attrs["target"].strip()}).first()
        if target is None:
            raise serializers.ValidationError({"target": ["Élément introuvable."]})
        attrs["target"] = target
        return attrs


class FollowerSerializer(serializers.ModelSerializer):
    follower = AuthorSerializer(read_only=True)

    class Meta:
        model = Follow
        fields = ["id", "follower", "created_at"]
        read_only_fields = fields


class FollowStatsSerializer(serializers.Serializer):
    followers = serializers.IntegerField()
    following = serializers.IntegerField()
