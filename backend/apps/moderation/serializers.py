"""Sérialiseurs de modération. Le signaleur n'est jamais révélé au membre visé."""

from typing import Any

from rest_framework import serializers

from apps.community.serializers import AuthorSerializer

from . import targets
from .models import AuditLog, ModerationAction, Report, TargetType
from .services import MAX_SUSPENSION_DAYS

REPORTABLE_TYPES = [
    TargetType.POST,
    TargetType.COMMENT,
    TargetType.ANSWER,
    TargetType.PROFILE,
    TargetType.PROJECT,
]


class ReportCreateSerializer(serializers.Serializer):
    target_type = serializers.ChoiceField(choices=TargetType.choices)
    target_id = serializers.UUIDField()
    reason = serializers.ChoiceField(choices=Report.Reason.choices)
    details = serializers.CharField(required=False, allow_blank=True, max_length=2000)

    def validate_target_type(self, value: str) -> str:
        if targets.get_spec(value) is None:
            raise serializers.ValidationError("Ce type de contenu ne peut pas être signalé.")
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs["reason"] == Report.Reason.OTHER and len(attrs.get("details", "").strip()) < 10:
            raise serializers.ValidationError(
                {"details": ["Précisez le motif (10 caractères minimum)."]}
            )
        return attrs


class MyReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = [
            "id",
            "target_type",
            "target_id",
            "reason",
            "details",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ModerationActionSerializer(serializers.ModelSerializer):
    moderator = serializers.CharField(source="moderator.username", read_only=True)

    class Meta:
        model = ModerationAction
        fields = [
            "id",
            "report",
            "moderator",
            "target_type",
            "target_id",
            "action_type",
            "reason",
            "previous_state",
            "new_state",
            "expires_at",
            "created_at",
        ]
        read_only_fields = fields


class ModerationReportSerializer(serializers.ModelSerializer):
    reporter = serializers.CharField(source="reporter.username", read_only=True)
    assigned_to = serializers.CharField(
        source="assigned_to.username", read_only=True, allow_null=True
    )
    target = serializers.SerializerMethodField()
    target_author = serializers.SerializerMethodField()
    open_reports_on_target = serializers.SerializerMethodField()
    can_handle = serializers.SerializerMethodField()
    actions = ModerationActionSerializer(many=True, read_only=True)

    class Meta:
        model = Report
        fields = [
            "id",
            "reporter",
            "target_type",
            "target_id",
            "target",
            "target_author",
            "reason",
            "details",
            "status",
            "assigned_to",
            "open_reports_on_target",
            "can_handle",
            "resolution_note",
            "resolved_at",
            "actions",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def _target(self, report: Report) -> tuple[Any, Any]:
        cache = self.context.setdefault("_targets", {})
        key = (report.target_type, report.target_id)
        if key not in cache:
            spec = targets.get_spec(report.target_type)
            cache[key] = (spec, spec.loader(report.target_id) if spec else None)
        return cache[key]

    def get_target(self, report: Report) -> dict[str, Any] | None:
        spec, target = self._target(report)
        return spec.preview(target) if target is not None else None

    def get_target_author(self, report: Report) -> dict[str, Any] | None:
        spec, target = self._target(report)
        if target is None:
            return None
        return AuthorSerializer(spec.author(target), context=self.context).data

    def get_open_reports_on_target(self, report: Report) -> int:
        return Report.objects.filter(
            target_type=report.target_type,
            target_id=report.target_id,
            status__in=Report.OPEN_STATUSES,
        ).count()

    def get_can_handle(self, report: Report) -> bool:
        request = self.context.get("request")
        spec, target = self._target(report)
        if request is None or target is None:
            return False
        author = spec.author(target)
        return (
            report.reporter_id != request.user.pk and getattr(author, "pk", None) != request.user.pk
        )


class ActionInputSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=ModerationAction.ActionType.choices)
    reason = serializers.CharField(
        min_length=5, max_length=1000, help_text="Motif journalisé et communiqué au membre."
    )
    duration_days = serializers.IntegerField(
        min_value=1,
        max_value=MAX_SUSPENSION_DAYS,
        required=False,
        allow_null=True,
        help_text="Durée de la suspension (SUSPEND uniquement).",
    )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs["action"] == ModerationAction.ActionType.SUSPEND and not attrs.get(
            "duration_days"
        ):
            raise serializers.ValidationError(
                {"duration_days": ["Durée obligatoire pour une suspension."]}
            )
        return attrs


class DirectActionSerializer(ActionInputSerializer):
    target_type = serializers.ChoiceField(choices=TargetType.choices)
    target_id = serializers.UUIDField()


class AuditLogSerializer(serializers.ModelSerializer):
    actor = serializers.CharField(source="actor.username", read_only=True, allow_null=True)

    class Meta:
        model = AuditLog
        fields = ["id", "actor", "action", "target_type", "target_id", "metadata", "created_at"]
        read_only_fields = fields


class StatsSerializer(serializers.Serializer):
    members = serializers.IntegerField()
    active_members = serializers.IntegerField()
    suspended_members = serializers.IntegerField()
    published_posts = serializers.IntegerField()
    questions = serializers.IntegerField()
    answers = serializers.IntegerField()
    projects = serializers.IntegerField()
    open_reports = serializers.IntegerField()
    hidden_contents = serializers.IntegerField()
    actions_last_30_days = serializers.IntegerField()
