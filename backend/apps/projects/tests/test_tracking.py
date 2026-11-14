"""Suivi avancé de projet (P1) : jalons, commentaires, mises à jour, activité, Kanban, invitations."""

import pytest

from apps.accounts.tests.factories import UserFactory
from apps.notifications.models import Notification
from apps.projects.models import (
    JoinRequest,
    Milestone,
    Project,
    ProjectActivity,
    ProjectInvitation,
    ProjectMember,
)
from apps.projects.tests.factories import TaskFactory, add_member, make_project

pytestmark = pytest.mark.django_db

Role = ProjectMember.Role


@pytest.fixture
def team(user):
    project = make_project(user)
    return {
        "project": project,
        "owner": user,
        "manager": add_member(project, role=Role.MANAGER).user,
        "contributor": add_member(project, role=Role.CONTRIBUTOR).user,
        "observer": add_member(project, role=Role.OBSERVER).user,
        "outsider": UserFactory(),
    }


def url(project, suffix):
    return f"/api/v1/projects/{project.slug}/{suffix}"


class TestMilestones:
    def test_manager_creates_and_completes_milestone(self, client_for, api_client, team):
        project, client = team["project"], client_for(team["manager"])

        created = client.post(
            url(project, "milestones/"), {"title": "Version bêta", "due_date": "2026-12-15"}
        )
        milestone_id = created.json()["id"]
        task = TaskFactory(project=project)
        client.patch(f"/api/v1/tasks/{task.id}/", {"milestone": milestone_id}, format="json")
        completed = client.patch(
            url(project, f"milestones/{milestone_id}/"), {"status": "COMPLETED"}
        )

        assert created.status_code == 201
        assert completed.json()["completed_at"] is not None
        assert api_client.get(url(project, "milestones/")).json()[0]["task_count"] == 1
        verbs = set(ProjectActivity.objects.filter(project=project).values_list("verb", flat=True))
        assert {"MILESTONE_CREATED", "MILESTONE_COMPLETED", "TASK_UPDATED"} <= verbs

        reopened = client.patch(url(project, f"milestones/{milestone_id}/"), {"status": "OPEN"})
        assert reopened.json()["completed_at"] is None
        assert client.delete(url(project, f"milestones/{milestone_id}/")).status_code == 204

    @pytest.mark.parametrize("who", ["contributor", "observer", "outsider"])
    def test_others_cannot_manage_milestones(self, client_for, team, who):
        response = client_for(team[who]).post(
            url(team["project"], "milestones/"), {"title": "Jalon"}
        )

        assert response.status_code == 403

    def test_task_milestone_must_belong_to_project(self, client_for, team):
        foreign = Milestone.objects.create(project=make_project(), title="Ailleurs")

        response = client_for(team["owner"]).post(
            url(team["project"], "tasks/"),
            {"title": "Tâche", "milestone": str(foreign.id)},
            format="json",
        )

        assert response.status_code == 400


class TestTaskComments:
    def test_members_comment_and_assignee_is_notified(self, client_for, team):
        task = TaskFactory(project=team["project"], assignee=team["contributor"])

        response = client_for(team["manager"]).post(
            f"/api/v1/tasks/{task.id}/comments/", {"content": "Où en es-tu ?"}
        )

        assert response.status_code == 201
        assert (
            client_for(team["observer"])
            .get(f"/api/v1/tasks/{task.id}/comments/")
            .json()[0]["content"]
            == "Où en es-tu ?"
        )
        assert Notification.objects.filter(recipient=team["contributor"]).exists()

    def test_observers_and_outsiders_cannot_comment(self, client_for, team):
        task = TaskFactory(project=team["project"])

        assert (
            client_for(team["observer"])
            .post(f"/api/v1/tasks/{task.id}/comments/", {"content": "x"})
            .status_code
            == 403
        )
        assert (
            client_for(team["outsider"])
            .post(f"/api/v1/tasks/{task.id}/comments/", {"content": "x"})
            .status_code
            == 404
        )

    def test_empty_comment(self, client_for, team):
        task = TaskFactory(project=team["project"])

        response = client_for(team["owner"]).post(
            f"/api/v1/tasks/{task.id}/comments/", {"content": "<b></b>"}
        )

        assert response.status_code == 400


class TestUpdatesAndActivity:
    def test_updates_are_public_and_notify_members(self, client_for, api_client, team):
        response = client_for(team["owner"]).post(
            url(team["project"], "updates/"),
            {"title": "Première démo", "content": "<p>La bêta est en ligne <script>x</script></p>"},
        )

        assert response.status_code == 201
        assert "script" not in response.json()["content"]
        assert api_client.get(url(team["project"], "updates/")).json()["count"] == 1
        assert Notification.objects.filter(
            recipient=team["contributor"], type="PROJECT_UPDATED"
        ).exists()
        assert (
            client_for(team["contributor"])
            .post(url(team["project"], "updates/"), {"title": "x", "content": "y"})
            .status_code
            == 403
        )

    def test_activity_is_reserved_to_members(self, client_for, team):
        client_for(team["owner"]).patch(url(team["project"], ""), {"status": "IN_PROGRESS"})

        body = client_for(team["observer"]).get(url(team["project"], "activity/")).json()

        assert {item["verb"] for item in body["results"]} >= {"PROJECT_CREATED", "STATUS_CHANGED"}
        assert (
            client_for(team["outsider"]).get(url(team["project"], "activity/")).status_code == 403
        )

    def test_history_records_team_changes(self, client_for, team):
        owner = client_for(team["owner"])
        member = ProjectMember.objects.get(project=team["project"], user=team["contributor"])
        owner.patch(url(team["project"], f"members/{member.id}/"), {"role": "OBSERVER"})
        owner.delete(url(team["project"], f"members/{member.id}/"))
        client_for(team["observer"]).post(url(team["project"], "leave/"))

        verbs = list(
            ProjectActivity.objects.filter(project=team["project"]).values_list("verb", flat=True)
        )

        assert {"ROLE_CHANGED", "MEMBER_REMOVED", "MEMBER_LEFT"} <= set(verbs)


class TestBoard:
    def test_board_groups_tasks_by_status(self, client_for, team):
        TaskFactory(project=team["project"], status="IN_PROGRESS")
        TaskFactory(project=team["project"])

        columns = client_for(team["observer"]).get(url(team["project"], "board/")).json()

        assert [column["status"] for column in columns] == [
            "TODO",
            "IN_PROGRESS",
            "IN_REVIEW",
            "DONE",
            "BLOCKED",
        ]
        assert len(columns[0]["tasks"]) == 1 and len(columns[1]["tasks"]) == 1
        assert client_for(team["outsider"]).get(url(team["project"], "board/")).status_code == 403


class TestInvitations:
    def test_invite_accept_creates_membership(self, client_for, team):
        guest = UserFactory(username="invitee")
        JoinRequest.objects.create(
            project=team["project"], user=guest, message="Je postule aussi en parallèle."
        )

        invitation = client_for(team["owner"]).post(
            url(team["project"], "invitations/"),
            {"username": "invitee", "role": "CONTRIBUTOR", "message": "Rejoins-nous !"},
        )
        assert invitation.status_code == 201, invitation.json()
        assert Notification.objects.get(recipient=guest).type == "PROJECT_INVITATION"
        assert client_for(guest).get("/api/v1/invitations/mine/").json()["count"] == 1

        accepted = client_for(guest).post(f"/api/v1/invitations/{invitation.json()['id']}/accept/")

        assert accepted.json()["status"] == "ACCEPTED"
        assert ProjectMember.objects.filter(
            project=team["project"], user=guest, status="ACTIVE"
        ).exists()
        assert JoinRequest.objects.get(user=guest).status == "ACCEPTED"

    def test_invitation_rules(self, client_for, team):
        owner = client_for(team["owner"])
        project = team["project"]
        UserFactory(username="cible")

        assert (
            client_for(team["manager"])
            .post(url(project, "invitations/"), {"username": "cible"})
            .status_code
            == 403
        )
        assert (
            owner.post(
                url(project, "invitations/"), {"username": team["contributor"].username}
            ).json()["code"]
            == "already_member"
        )
        assert owner.post(url(project, "invitations/"), {"username": "cible"}).status_code == 201
        assert (
            owner.post(url(project, "invitations/"), {"username": "cible"}).json()["code"]
            == "duplicate_invitation"
        )
        assert (
            owner.post(
                url(project, "invitations/"), {"username": "cible", "role": "OWNER"}
            ).status_code
            == 400
        )
        assert owner.get(url(project, "invitations/")).json()["count"] == 1

    def test_only_owner_invites_managers(self, client_for, team):
        habilitated = add_member(team["project"], role=Role.MANAGER, can_manage_members=True).user
        UserFactory(username="futur_resp")

        response = client_for(habilitated).post(
            url(team["project"], "invitations/"), {"username": "futur_resp", "role": "MANAGER"}
        )

        assert response.status_code == 403

    def test_decline_cancel_and_privacy(self, client_for, team):
        guest, other = UserFactory(), UserFactory()
        owner = client_for(team["owner"])
        first = owner.post(
            url(team["project"], "invitations/"), {"username": guest.username}
        ).json()
        second = owner.post(
            url(team["project"], "invitations/"), {"username": other.username}
        ).json()

        assert client_for(other).get(f"/api/v1/invitations/{first['id']}/").status_code == 404
        assert (
            client_for(team["owner"]).post(f"/api/v1/invitations/{first['id']}/accept/").status_code
            == 403
        )
        assert (
            client_for(guest).post(f"/api/v1/invitations/{first['id']}/decline/").json()["status"]
            == "DECLINED"
        )
        assert (
            client_for(guest).post(f"/api/v1/invitations/{first['id']}/accept/").status_code == 409
        )
        assert (
            client_for(other).post(f"/api/v1/invitations/{second['id']}/cancel/").status_code == 403
        )
        assert (
            owner.post(f"/api/v1/invitations/{second['id']}/cancel/").json()["status"]
            == "CANCELLED"
        )

    def test_no_invitation_on_archived_project(self, client_for, team):
        Project.objects.filter(pk=team["project"].pk).update(status=Project.Status.ARCHIVED)
        UserFactory(username="tardif")

        response = client_for(team["owner"]).post(
            url(team["project"], "invitations/"), {"username": "tardif"}
        )

        assert response.json()["code"] == "project_archived"
        assert not ProjectInvitation.objects.exists()
