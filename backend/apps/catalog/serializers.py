"""Sérialiseurs des référentiels."""

from typing import Any

from rest_framework import serializers

from .models import Category, Country, Tag, Technology
from .normalization import make_slug, normalize_label


class ReferenceSerializerMixin(serializers.ModelSerializer):
    """Normalise le nom et refuse les doublons de slug (« React » / « react »)."""

    def validate_name(self, value: str) -> str:
        value = normalize_label(value)
        slug = make_slug(value)
        if not slug:
            raise serializers.ValidationError("Le nom doit contenir une lettre ou un chiffre.")
        duplicates = self.Meta.model.objects.filter(slug=slug)
        if self.instance is not None:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError("Un élément portant ce nom existe déjà.")
        return value

    def update(self, instance: Any, validated_data: dict[str, Any]) -> Any:
        if "name" in validated_data:
            instance.slug = make_slug(validated_data["name"])
        return super().update(instance, validated_data)


class CategorySerializer(ReferenceSerializerMixin):
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "description", "sort_order", "is_active"]
        read_only_fields = ["id", "slug"]


class TagSerializer(ReferenceSerializerMixin):
    class Meta:
        model = Tag
        fields = ["id", "name", "slug", "is_active"]
        read_only_fields = ["id", "slug"]


class TechnologySerializer(ReferenceSerializerMixin):
    category = serializers.SlugRelatedField(
        slug_field="slug", queryset=Category.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = Technology
        fields = ["id", "name", "slug", "category", "is_active"]
        read_only_fields = ["id", "slug"]


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ["id", "code", "name", "is_active"]
        read_only_fields = ["id"]

    def validate_code(self, value: str) -> str:
        value = value.strip().upper()
        if len(value) != 2 or not value.isalpha():
            raise serializers.ValidationError("Code ISO 3166-1 alpha-2 attendu (ex. SN).")
        return value


class TechnologyRefSerializer(serializers.ModelSerializer):
    """Représentation compacte utilisée dans les autres ressources."""

    class Meta:
        model = Technology
        fields = ["id", "name", "slug"]


class TagRefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name", "slug"]


class CategoryRefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug"]


class CountryRefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ["code", "name"]
