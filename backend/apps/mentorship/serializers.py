from rest_framework import serializers

from apps.accounts.models import User
from apps.catalog.models import Category, Technology
from apps.catalog.serializers import CategoryRefSerializer, TechnologyRefSerializer
from apps.community.serializers import AuthorSerializer
from apps.profiles.models import Language

from .models import MentorProfile, MentorshipFeedback, MentorshipRequest, MentorshipSession


class MentorSerializer(serializers.ModelSerializer):
    user = AuthorSerializer(read_only=True)
    domains = CategoryRefSerializer(many=True, read_only=True)
    technologies = TechnologyRefSerializer(many=True, read_only=True)
    active_mentees = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = MentorProfile
        fields = [
            "id",
            "user",
            "headline",
            "bio",
            "domains",
            "technologies",
            "languages",
            "is_available",
            "max_active_mentees",
            "active_mentees",
        ]
        read_only_fields = fields


class MentorWriteSerializer(serializers.ModelSerializer):
    domains = serializers.SlugRelatedField(
        slug_field="slug",
        many=True,
        required=False,
        queryset=Category.objects.filter(is_active=True),
    )
    technologies = serializers.SlugRelatedField(
        slug_field="slug",
        many=True,
        required=False,
        queryset=Technology.objects.filter(is_active=True),
    )
    languages = serializers.ListField(
        child=serializers.ChoiceField(choices=Language.choices), required=False, max_length=8
    )

    class Meta:
        model = MentorProfile
        fields = [
            "headline",
            "bio",
            "domains",
            "technologies",
            "languages",
            "is_available",
            "max_active_mentees",
        ]


class MentorshipRequestSerializer(serializers.ModelSerializer):
    mentee = AuthorSerializer(read_only=True)
    mentor = AuthorSerializer(source="mentor.user", read_only=True)

    class Meta:
        model = MentorshipRequest
        fields = [
            "id",
            "mentee",
            "mentor",
            "goal",
            "status",
            "response_message",
            "responded_at",
            "completed_at",
            "created_at",
        ]
        read_only_fields = fields


class MentorshipRequestCreateSerializer(serializers.Serializer):
    mentor = serializers.SlugRelatedField(
        slug_field="username",
        queryset=User.objects.filter(is_active=True, mentor_profile__isnull=False),
    )
    goal = serializers.CharField(min_length=MentorshipRequest.GOAL_MIN_LENGTH, max_length=2000)


class RespondSerializer(serializers.Serializer):
    accept = serializers.BooleanField()
    message = serializers.CharField(required=False, allow_blank=True, max_length=500)


class SessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MentorshipSession
        fields = [
            "id",
            "scheduled_at",
            "duration_minutes",
            "meeting_url",
            "agenda",
            "notes",
            "status",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate_meeting_url(self, value: str) -> str:
        if value and not value.lower().startswith(("http://", "https://")):
            raise serializers.ValidationError("Seuls les liens http et https sont acceptés.")
        return value


class FeedbackSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)

    class Meta:
        model = MentorshipFeedback
        fields = ["id", "author", "rating", "comment", "created_at"]
        read_only_fields = ["id", "author", "created_at"]
