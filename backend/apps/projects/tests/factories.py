import factory

from apps.accounts.tests.factories import UserFactory
from apps.projects.models import Project, ProjectMember, ProjectRoleNeed, ProjectTask
from apps.projects.services import create_project


def make_project(owner=None, **data) -> Project:
    """Crée un projet via le service, comme l'API (le propriétaire devient membre)."""
    owner = owner or UserFactory()
    fields = {"name": "Plateforme de covoiturage étudiant", "short_description": "Covoiturage"}
    fields.update(data)
    return create_project(owner=owner, data=fields)


def add_member(project: Project, user=None, role=ProjectMember.Role.CONTRIBUTOR, **extra):
    return ProjectMember.objects.create(
        project=project, user=user or UserFactory(), role=role, **extra
    )


class RoleNeedFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProjectRoleNeed

    role_name = "Développeur·se backend"
    slots = 1


class TaskFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProjectTask

    title = factory.Sequence(lambda n: f"Tâche {n}")
    created_by = factory.LazyAttribute(lambda task: task.project.owner)
