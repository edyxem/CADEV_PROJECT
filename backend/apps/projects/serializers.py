"""Sérialiseurs des projets. Les demandes ne sont visibles que du candidat et des gestionnaires."""

from typing import Any

from rest_framework import serializers

from apps.accounts.models import User
from apps.catalog.models import Category, Technology
from apps.catalog.serializers import CategoryRefSerializer, TechnologyRefSerializer
from apps.community.serializers import AuthorSerializer

from . import policies
from .models import JoinRequest, Project, ProjectMember, ProjectRoleNeed, ProjectTask


class RoleNeedSerializer(serializers.ModelSerializer):
    required_technologies = TechnologyRefSerializer(many=True, read_only=True)

    class Meta:
        model = ProjectRoleNeed
        fields = [
            "id",
            "role_name",
            "description",
            "expected_level",
            "required_technologies",
            "slots",
            "is_open",
        ]
        read_only_fields = ["id"]


class RoleNeedWriteSerializer(serializers.ModelSerializer):
    required_technologies = serializers.SlugRelatedField(
        slug_field="slug",
        many=True,
        required=False,
        queryset=Technology.objects.filter(is_active=True),
    )

    class Meta:
        model = ProjectRoleNeed
        fields = [
            "role_name",
            "description",
            "expected_level",
            "required_technologies",
            "slots",
            "is_open",
        ]


class ProjectListSerializer(serializers.ModelSerializer):
    owner = AuthorSerializer(read_only=True)
    category = CategoryRefSerializer(read_only=True)
    technologies = TechnologyRefSerializer(many=True, read_only=True)
    member_count = serializers.IntegerField(read_only=True)
    open_role_count = serializers.IntegerField(read_only=True)
    is_accepting_members = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "id",
            "slug",
            "name",
            "short_description",
            "logo",
            "owner",
            "category",
            "technologies",
            "status",
            "visibility",
            "collaboration_mode",
            "member_count",
            "open_role_count",
            "is_accepting_members",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_is_accepting_members(self, project: Project) -> bool:
        from .models import JOINABLE_STATUSES

        return project.accepts_join_requests and project.status in JOINABLE_STATUSES


class ProjectDetailSerializer(ProjectListSerializer):
    role_needs = RoleNeedSerializer(many=True, read_only=True)
    my_role = serializers.SerializerMethodField(help_text="Rôle du lecteur dans le projet.")
    permissions = serializers.SerializerMethodField()
    task_stats = serializers.SerializerMethodField()

    class Meta(ProjectListSerializer.Meta):
        fields = [
            *ProjectListSerializer.Meta.fields,
            "description",
            "problem",
            "objectives",
            "expected_availability",
            "accepts_join_requests",
            "repository_url",
            "demo_url",
            "completed_at",
            "role_needs",
            "my_role",
            "permissions",
            "task_stats",
        ]
        read_only_fields = fields

    def _user(self) -> Any:
        request = self.context.get("request")
        return request.user if request else None

    def get_my_role(self, project: Project) -> str | None:
        return policies.role_of(project, self._user())

    def get_permissions(self, project: Project) -> dict[str, bool]:
        user = self._user()
        return {
            "edit_settings": policies.can_edit_settings(project, user),
            "manage_members": policies.can_manage_members(project, user),
            "manage_tasks": policies.can_manage_tasks(project, user),
            "create_tasks": policies.can_contribute(project, user),
            "view_tasks": policies.can_view_tasks(project, user),
        }

    def get_task_stats(self, project: Project) -> dict[str, int]:
        from .selectors import task_stats

        return task_stats(project)


class ProjectWriteSerializer(serializers.ModelSerializer):
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
        model = Project
        fields = [
            "name",
            "short_description",
            "description",
            "problem",
            "objectives",
            "category",
            "technologies",
            "status",
            "visibility",
            "collaboration_mode",
            "expected_availability",
            "accepts_join_requests",
            "repository_url",
            "demo_url",
        ]

    def validate_name(self, value: str) -> str:
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Le nom doit contenir au moins 3 caractères.")
        return value

    def validate_technologies(self, value: list) -> list:
        if len(value) > 12:
            raise serializers.ValidationError("12 technologies au maximum.")
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        for field in ("repository_url", "demo_url"):
            url = attrs.get(field, "")
            if url and not url.lower().startswith(("http://", "https://")):
                raise serializers.ValidationError(
                    {field: ["Seuls les liens http et https sont acceptés."]}
                )
        return attrs


class MemberSerializer(serializers.ModelSerializer):
    user = AuthorSerializer(read_only=True)

    class Meta:
        model = ProjectMember
        fields = ["id", "user", "role", "title", "can_manage_members", "status", "joined_at"]
        read_only_fields = fields


class MemberUpdateSerializer(serializers.ModelSerializer):
    role = serializers.ChoiceField(
        choices=[
            (r, label) for r, label in ProjectMember.Role.choices if r != ProjectMember.Role.OWNER
        ],
        required=False,
    )

    class Meta:
        model = ProjectMember
        fields = ["role", "title", "can_manage_members"]


class JoinRequestSerializer(serializers.ModelSerializer):
    user = AuthorSerializer(read_only=True)
    project = serializers.SerializerMethodField()
    requested_role = RoleNeedSerializer(read_only=True)

    class Meta:
        model = JoinRequest
        fields = [
            "id",
            "project",
            "user",
            "requested_role",
            "message",
            "status",
            "response_message",
            "can_reapply",
            "reviewed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_project(self, join_request: JoinRequest) -> dict[str, str]:
        return {
            "id": str(join_request.project_id),
            "slug": join_request.project.slug,
            "name": join_request.project.name,
        }


class JoinRequestCreateSerializer(serializers.Serializer):
    message = serializers.CharField(min_length=JoinRequest.MESSAGE_MIN_LENGTH, max_length=2000)
    requested_role = serializers.UUIDField(required=False, allow_null=True)


class JoinRequestDecisionSerializer(serializers.Serializer):
    role = serializers.ChoiceField(
        choices=[
            ProjectMember.Role.CONTRIBUTOR,
            ProjectMember.Role.OBSERVER,
            ProjectMember.Role.MANAGER,
        ],
        default=ProjectMember.Role.CONTRIBUTOR,
        help_text="Rôle attribué à l'acceptation (MANAGER : propriétaire uniquement).",
    )
    response_message = serializers.CharField(required=False, allow_blank=True, max_length=500)


class TransferOwnershipSerializer(serializers.Serializer):
    username = serializers.SlugRelatedField(
        slug_field="username", queryset=User.objects.filter(is_active=True)
    )


class TaskSerializer(serializers.ModelSerializer):
    assignee = AuthorSerializer(read_only=True, allow_null=True)
    created_by = AuthorSerializer(read_only=True)
    can_edit = serializers.SerializerMethodField()

    class Meta:
        model = ProjectTask
        fields = [
            "id",
            "project",
            "title",
            "description",
            "assignee",
            "created_by",
            "status",
            "priority",
            "due_date",
            "completed_at",
            "can_edit",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_can_edit(self, task: ProjectTask) -> bool:
        request = self.context.get("request")
        return bool(request and policies.can_edit_task(task, request.user))


class TaskWriteSerializer(serializers.ModelSerializer):
    assignee = serializers.SlugRelatedField(
        slug_field="username",
        queryset=User.objects.filter(is_active=True),
        required=False,
        allow_null=True,
        help_text="Nom d'utilisateur d'un membre actif du projet.",
    )

    class Meta:
        model = ProjectTask
        fields = ["title", "description", "assignee", "status", "priority", "due_date"]

    def validate_title(self, value: str) -> str:
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Le titre doit contenir au moins 3 caractères.")
        return value


class ProjectRefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ["id", "slug", "name", "status"]
