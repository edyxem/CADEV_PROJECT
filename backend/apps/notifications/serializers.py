from rest_framework import serializers

from .models import MANDATORY_TYPES, Notification, NotificationPreference


class ActorSerializer(serializers.Serializer):
    username = serializers.CharField()


class NotificationSerializer(serializers.ModelSerializer):
    actor = ActorSerializer(read_only=True, allow_null=True)
    type_label = serializers.CharField(source="get_type_display", read_only=True)

    class Meta:
        model = Notification
        fields = [
            "id",
            "type",
            "type_label",
            "title",
            "message",
            "actor",
            "target_type",
            "target_id",
            "target_url",
            "is_read",
            "read_at",
            "created_at",
        ]
        read_only_fields = fields


class UnreadCountSerializer(serializers.Serializer):
    unread = serializers.IntegerField()


class MarkedSerializer(serializers.Serializer):
    updated = serializers.IntegerField()


class PreferenceSerializer(serializers.ModelSerializer):
    muted_types = serializers.ListField(
        child=serializers.ChoiceField(choices=Notification.Type.choices), required=False
    )
    email_types = serializers.ListField(
        child=serializers.ChoiceField(choices=Notification.Type.choices), required=False
    )
    mandatory_types = serializers.SerializerMethodField()

    class Meta:
        model = NotificationPreference
        fields = ["muted_types", "email_types", "mandatory_types", "updated_at"]
        read_only_fields = ["mandatory_types", "updated_at"]

    def get_mandatory_types(self, preferences: NotificationPreference) -> list[str]:
        return sorted(MANDATORY_TYPES)

    def validate_muted_types(self, value: list[str]) -> list[str]:
        if MANDATORY_TYPES & set(value):
            raise serializers.ValidationError(
                "Les décisions de modération ne peuvent pas être masquées."
            )
        return sorted(set(value))

    def validate_email_types(self, value: list[str]) -> list[str]:
        return sorted(set(value))
