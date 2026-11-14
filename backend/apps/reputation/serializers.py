from rest_framework import serializers

from apps.catalog.models import Technology
from apps.catalog.serializers import TechnologyRefSerializer
from apps.community.serializers import AuthorSerializer

from .models import Achievement, Recommendation, UserAchievement


class AchievementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Achievement
        fields = ["code", "name", "description", "icon_key", "event_type", "threshold"]
        read_only_fields = fields


class UserAchievementSerializer(serializers.ModelSerializer):
    code = serializers.CharField(source="achievement.code")
    name = serializers.CharField(source="achievement.name")
    description = serializers.CharField(source="achievement.description")
    icon_key = serializers.CharField(source="achievement.icon_key")

    class Meta:
        model = UserAchievement
        fields = ["code", "name", "description", "icon_key", "awarded_at"]
        read_only_fields = fields


class BreakdownSerializer(serializers.Serializer):
    event_type = serializers.CharField()
    label = serializers.CharField()
    count = serializers.IntegerField()
    points = serializers.IntegerField()
    points_per_event = serializers.IntegerField()


class ReputationSerializer(serializers.Serializer):
    username = serializers.CharField()
    score = serializers.IntegerField()
    breakdown = BreakdownSerializer(many=True)
    achievements = UserAchievementSerializer(many=True)
    explanation = serializers.CharField()


class RecommendationSerializer(serializers.ModelSerializer):
    recommender = AuthorSerializer(read_only=True)
    technology = TechnologyRefSerializer(read_only=True)

    class Meta:
        model = Recommendation
        fields = ["id", "recommender", "technology", "context", "created_at"]
        read_only_fields = fields


class RecommendationCreateSerializer(serializers.Serializer):
    context = serializers.CharField(
        min_length=Recommendation.CONTEXT_MIN_LENGTH,
        max_length=1000,
        help_text="Contexte concret de la collaboration (30 caractères minimum).",
    )
    technology = serializers.SlugRelatedField(
        slug_field="slug",
        queryset=Technology.objects.filter(is_active=True),
        required=False,
        allow_null=True,
    )


class DashboardSerializer(serializers.Serializer):
    reputation = serializers.IntegerField()
    achievements = serializers.IntegerField()
    posts = serializers.IntegerField()
    drafts = serializers.IntegerField()
    answers = serializers.IntegerField()
    accepted_answers = serializers.IntegerField()
    bookmarks = serializers.IntegerField()
    unread_notifications = serializers.IntegerField()
    projects = serializers.IntegerField()
    open_tasks = serializers.IntegerField()
    join_requests_to_review = serializers.IntegerField()
    pending_join_requests = serializers.IntegerField()
    followers = serializers.IntegerField()
    following = serializers.IntegerField()
