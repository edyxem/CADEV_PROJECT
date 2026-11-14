from typing import Any

from rest_framework import serializers

from apps.catalog.models import Category, Technology
from apps.catalog.serializers import CategoryRefSerializer, TechnologyRefSerializer
from apps.communities.models import Community
from apps.community.serializers import AuthorSerializer

from . import services
from .models import Event, EventRegistration


class EventSerializer(serializers.ModelSerializer):
    organizer = AuthorSerializer(read_only=True)
    community = serializers.SlugRelatedField(slug_field="slug", read_only=True)
    category = CategoryRefSerializer(read_only=True)
    technologies = TechnologyRefSerializer(many=True, read_only=True)
    registered_count = serializers.IntegerField(read_only=True, default=0)
    is_registered = serializers.SerializerMethodField()
    is_past = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            "id",
            "title",
            "description",
            "kind",
            "format",
            "starts_at",
            "ends_at",
            "location",
            "online_url",
            "capacity",
            "registered_count",
            "is_registered",
            "is_past",
            "organizer",
            "community",
            "category",
            "technologies",
            "status",
            "created_at",
        ]
        read_only_fields = fields

    def _user(self) -> Any:
        request = self.context.get("request")
        return request.user if request else None

    def get_is_registered(self, event: Event) -> bool:
        return services.is_registered(event, self._user())

    def get_is_past(self, event: Event) -> bool:
        from django.utils import timezone

        return event.ends_at <= timezone.now()

    def to_representation(self, event: Event) -> dict[str, Any]:
        data = super().to_representation(event)
        user = self._user()
        organizer = user is not None and user.is_authenticated and user.pk == event.organizer_id
        if not organizer and not data["is_registered"]:
            data["online_url"] = None  # lien réservé aux inscrits
        return data


class EventWriteSerializer(serializers.ModelSerializer):
    community = serializers.SlugRelatedField(
        slug_field="slug",
        queryset=Community.objects.filter(hidden_by_moderation=False),
        required=False,
        allow_null=True,
    )
    category = serializers.SlugRelatedField(
        slug_field="slug",
        queryset=Category.objects.filter(is_active=True),
        required=False,
        allow_null=True,
    )
    technologies = serializers.SlugRelatedField(
        slug_field="slug",
        many=True,
        required=False,
        queryset=Technology.objects.filter(is_active=True),
    )

    class Meta:
        model = Event
        fields = [
            "title",
            "description",
            "kind",
            "format",
            "starts_at",
            "ends_at",
            "location",
            "online_url",
            "capacity",
            "community",
            "category",
            "technologies",
        ]

    def validate_online_url(self, value: str) -> str:
        if value and not value.lower().startswith(("http://", "https://")):
            raise serializers.ValidationError("Seuls les liens http et https sont acceptés.")
        return value


class RegistrationSerializer(serializers.ModelSerializer):
    user = AuthorSerializer(read_only=True)

    class Meta:
        model = EventRegistration
        fields = ["id", "user", "status", "created_at"]
        read_only_fields = fields
