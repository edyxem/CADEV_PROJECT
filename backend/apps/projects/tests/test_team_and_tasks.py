import pytest

from apps.accounts.tests.factories import UserFactory
from apps.notifications.models import Notification
from apps.projects.models import Project, ProjectMember, ProjectTask
from apps.projects.tests.factories import TaskFactory, add_member, make_project

pytestmark = pytest.mark.django_db

Role = ProjectMember.Role


@pytest.fixture
def team(user):
    """Projet de démonstration avec un membre de chaque rôle."""
    project = make_project(user)
    return {
        "project": project,
        "owner": user,
        "manager": add_member(project, role=Role.MANAGER).user,
        "habilitated": add_member(project, role=Role.MANAGER, can_manage_members=True).user,
        "contributor": add_member(project, role=Role.CONTRIBUTOR).user,
        "observer": add_member(project, role=Role.OBSERVER).user,
        "outsider": UserFactory(),
    }


def tasks_url(project):
    return f"/api/v1/projects/{project.slug}/tasks/"


def task_url(task):
    return f"/api/v1/tasks/{task.id}/"


def member_url(project, member):
    return f"/api/v1/projects/{project.slug}/members/{member.id}/"


def membership(team, key):
    return ProjectMember.objects.get(project=team["project"], user=team[key], status="ACTIVE")


class TestMemberManagement:
    def test_owner_changes_role_and_rights(self, client_for, team):
        member = membership(team, "contributor")

        response = client_for(team["owner"]).patch(
            member_url(team["project"], member),
            {"role": "MANAGER", "can_manage_members": True, "title": "Lead <b>backend</b>"},
            format="json",
        )

        assert response.status_code == 200
        assert response.json()["can_manage_members"] is True
        assert response.json()["title"] == "Lead backend"

    def test_habilitated_manager_handles_contributors_only(self, client_for, team):
        client = client_for(team["habilitated"])
        project = team["project"]

        assert (
            client.patch(
                member_url(project, membership(team, "contributor")), {"role": "OBSERVER"}
            ).status_code
            == 200
        )
        assert (
            client.patch(
                member_url(project, membership(team, "manager")), {"role": "OBSERVER"}
            ).status_code
            == 403
        )
        assert (
            client.patch(
                member_url(project, membership(team, "observer")), {"role": "MANAGER"}
            ).status_code
            == 403
        )
        assert (
            client.patch(member_url(project, membership(team, "owner")), {"title": "x"}).status_code
            == 403
        )

    @pytest.mark.parametrize("who", ["manager", "contributor", "observer", "outsider"])
    def test_others_cannot_manage_members(self, client_for, team, who):
        target = membership(team, "observer" if who != "observer" else "contributor")

        response = client_for(team[who]).delete(member_url(team["project"], target))

        assert (
            response.status_code in {403, 404} if who == "outsider" else response.status_code == 403
        )

    def test_owner_role_cannot_be_assigned_by_update(self, client_for, team):
        response = client_for(team["owner"]).patch(
            member_url(team["project"], membership(team, "contributor")), {"role": "OWNER"}
        )

        assert response.status_code == 400

    def test_removing_a_member_frees_open_tasks_but_keeps_done_ones(self, client_for, team):
        project, contributor = team["project"], team["contributor"]
        open_task = TaskFactory(project=project, assignee=contributor)
        done_task = TaskFactory(
            project=project,
            assignee=contributor,
            status="DONE",
            completed_at="2026-11-01T10:00:00Z",
        )

        response = client_for(team["owner"]).delete(
            member_url(project, membership(team, "contributor"))
        )

        assert response.status_code == 204
        open_task.refresh_from_db()
        done_task.refresh_from_db()
        assert open_task.assignee is None
        assert done_task.assignee == contributor

    def test_owner_and_managers_protection(self, client_for, team):
        project = team["project"]

        assert (
            client_for(team["owner"])
            .delete(member_url(project, membership(team, "owner")))
            .status_code
            == 403
        )
        assert (
            client_for(team["habilitated"])
            .delete(member_url(project, membership(team, "manager")))
            .status_code
            == 403
        )
        assert (
            client_for(team["owner"])
            .delete(member_url(project, membership(team, "manager")))
            .status_code
            == 204
        )

    def test_unknown_member_is_404(self, client_for, team):
        url = (
            f"/api/v1/projects/{team['project'].slug}/members/00000000-0000-0000-0000-000000000000/"
        )

        assert client_for(team["owner"]).delete(url).status_code == 404


class TestTaskAccess:
    def test_only_members_read_tasks(self, client_for, api_client, team):
        TaskFactory(project=team["project"])

        assert client_for(team["observer"]).get(tasks_url(team["project"])).json()["count"] == 1
        assert client_for(team["outsider"]).get(tasks_url(team["project"])).status_code == 403
        assert api_client.get(tasks_url(team["project"])).status_code == 401

    def test_task_detail_is_hidden_from_outsiders(self, client_for, team):
        task = TaskFactory(project=team["project"])

        assert client_for(team["outsider"]).get(task_url(task)).status_code == 404
        assert (
            client_for(team["outsider"]).patch(task_url(task), {"status": "DONE"}).status_code
            == 404
        )
        assert client_for(team["contributor"]).get(task_url(task)).status_code == 200

    def test_public_detail_exposes_progress_only(self, api_client, team):
        TaskFactory(project=team["project"], status="IN_PROGRESS")

        stats = api_client.get(f"/api/v1/projects/{team['project'].slug}/").json()["task_stats"]

        assert stats["IN_PROGRESS"] == 1 and stats["total"] == 1

    def test_filters(self, client_for, team):
        project = team["project"]
        TaskFactory(project=project, assignee=team["contributor"], status="IN_PROGRESS")
        TaskFactory(project=project)
        client = client_for(team["contributor"])

        assert client.get(tasks_url(project), {"assignee": "me"}).json()["count"] == 1
        assert client.get(tasks_url(project), {"status": "IN_PROGRESS"}).json()["count"] == 1
        assert (
            client.get(tasks_url(project), {"assignee": team["contributor"].username}).json()[
                "count"
            ]
            == 1
        )


class TestTaskCreation:
    def test_owner_creates_and_assigns_task(self, client_for, team):
        response = client_for(team["owner"]).post(
            tasks_url(team["project"]),
            {
                "title": "Mettre en place l'API",
                "assignee": team["contributor"].username,
                "priority": "HIGH",
            },
            format="json",
        )

        assert response.status_code == 201, response.json()
        assert response.json()["assignee"]["username"] == team["contributor"].username
        assert Notification.objects.get(recipient=team["contributor"]).type == "TASK_ASSIGNED"

    def test_contributor_creates_but_assigns_only_self(self, client_for, team):
        client = client_for(team["contributor"])
        project = team["project"]

        own = client.post(
            tasks_url(project),
            {"title": "Rédiger la doc", "assignee": team["contributor"].username},
        )
        other = client.post(
            tasks_url(project), {"title": "Tâche pour autrui", "assignee": team["owner"].username}
        )

        assert own.status_code == 201
        assert other.status_code == 403

    @pytest.mark.parametrize("who", ["observer", "outsider"])
    def test_observers_and_outsiders_cannot_create(self, client_for, team, who):
        response = client_for(team[who]).post(
            tasks_url(team["project"]), {"title": "Tâche interdite"}
        )

        assert response.status_code == 403

    def test_assignee_must_be_active_non_observer_member(self, client_for, team):
        client = client_for(team["owner"])
        project = team["project"]
        former = add_member(project).user
        ProjectMember.objects.filter(user=former).update(status="LEFT")

        for assignee, code in (
            (team["outsider"], "assignee_not_member"),
            (former, "assignee_not_member"),
            (team["observer"], "assignee_observer"),
        ):
            response = client.post(
                tasks_url(project), {"title": "Tâche", "assignee": assignee.username}
            )
            assert response.status_code == 409
            assert response.json()["code"] == code

    def test_task_created_done_has_completion_date(self, client_for, team):
        response = client_for(team["owner"]).post(
            tasks_url(team["project"]), {"title": "Déjà faite", "status": "DONE"}
        )

        assert response.json()["completed_at"] is not None

    def test_no_task_on_archived_project(self, client_for, team):
        Project.objects.filter(pk=team["project"].pk).update(status=Project.Status.ARCHIVED)

        response = client_for(team["owner"]).post(
            tasks_url(team["project"]), {"title": "Tâche tardive"}
        )

        assert response.status_code == 409


class TestTaskUpdates:
    def test_contributor_moves_own_assigned_task_to_done(self, client_for, team):
        task = TaskFactory(project=team["project"], assignee=team["contributor"])
        client = client_for(team["contributor"])

        assert client.patch(task_url(task), {"status": "IN_PROGRESS"}).status_code == 200
        response = client.patch(task_url(task), {"status": "DONE"})

        assert response.json()["status"] == "DONE"
        assert response.json()["completed_at"] is not None

    def test_contributor_cannot_touch_others_tasks(self, client_for, team):
        task = TaskFactory(project=team["project"], assignee=team["manager"])

        assert (
            client_for(team["contributor"]).patch(task_url(task), {"title": "Pirate"}).status_code
            == 403
        )

    def test_observer_is_read_only(self, client_for, team):
        task = TaskFactory(project=team["project"])

        assert (
            client_for(team["observer"])
            .patch(task_url(task), {"status": "IN_PROGRESS"})
            .status_code
            == 403
        )
        assert client_for(team["observer"]).delete(task_url(task)).status_code == 403

    def test_only_assignee_or_manager_marks_done(self, client_for, team):
        task = TaskFactory(project=team["project"], created_by=team["contributor"], assignee=None)

        assert (
            client_for(team["contributor"]).patch(task_url(task), {"status": "DONE"}).status_code
            == 403
        )
        assert (
            client_for(team["manager"]).patch(task_url(task), {"status": "DONE"}).status_code == 200
        )

    def test_reopening_done_task_is_reserved_to_managers(self, client_for, team):
        task = TaskFactory(project=team["project"], assignee=team["contributor"])
        client_for(team["contributor"]).patch(task_url(task), {"status": "DONE"})

        assert (
            client_for(team["contributor"])
            .patch(task_url(task), {"status": "IN_PROGRESS"})
            .status_code
            == 403
        )
        reopened = client_for(team["owner"]).patch(task_url(task), {"status": "IN_PROGRESS"})
        assert reopened.json()["completed_at"] is None

    def test_forbidden_status_transition(self, client_for, team):
        task = TaskFactory(project=team["project"], status="BLOCKED")

        response = client_for(team["owner"]).patch(task_url(task), {"status": "DONE"})

        assert response.status_code == 409
        assert response.json()["code"] == "invalid_transition"

    def test_owner_reassigns_and_new_assignee_is_notified(self, client_for, team):
        task = TaskFactory(project=team["project"], assignee=team["contributor"])

        response = client_for(team["owner"]).patch(
            task_url(task), {"assignee": team["manager"].username}
        )

        assert response.json()["assignee"]["username"] == team["manager"].username
        assert Notification.objects.filter(recipient=team["manager"], type="TASK_ASSIGNED").exists()

    def test_contributor_cannot_steal_assigned_task(self, client_for, team):
        task = TaskFactory(
            project=team["project"], created_by=team["contributor"], assignee=team["manager"]
        )

        response = client_for(team["contributor"]).patch(
            task_url(task), {"assignee": team["contributor"].username}
        )

        assert response.status_code == 403

    def test_contributor_takes_unassigned_task_he_created(self, client_for, team):
        task = TaskFactory(project=team["project"], created_by=team["contributor"])

        response = client_for(team["contributor"]).patch(
            task_url(task),
            {"assignee": team["contributor"].username, "title": "Titre <i>propre</i>"},
        )

        assert response.status_code == 200
        assert response.json()["title"] == "Titre propre"
        assert response.json()["can_edit"] is True


class TestTaskDeletion:
    def test_managers_delete_open_tasks_only(self, client_for, team):
        open_task = TaskFactory(project=team["project"])
        done_task = TaskFactory(
            project=team["project"], status="DONE", completed_at="2026-11-01T10:00:00Z"
        )

        assert client_for(team["contributor"]).delete(task_url(open_task)).status_code == 403
        assert client_for(team["manager"]).delete(task_url(done_task)).status_code == 409
        assert client_for(team["manager"]).delete(task_url(open_task)).status_code == 204
        assert ProjectTask.objects.filter(pk=done_task.pk).exists()
