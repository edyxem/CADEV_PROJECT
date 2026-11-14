from datetime import timedelta

import pytest
from django.db import IntegrityError
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.notifications.models import Notification
from apps.projects.models import JoinRequest, Project, ProjectMember
from apps.projects.tests.factories import RoleNeedFactory, add_member, make_project
from common.throttling import ScopedWriteThrottle

pytestmark = pytest.mark.django_db

MESSAGE = "Je maîtrise Django et j'aimerais contribuer au backend de ce projet."
Role = ProjectMember.Role


def requests_url(project):
    return f"/api/v1/projects/{project.slug}/join-requests/"


def apply(client, project, **extra):
    return client.post(requests_url(project), {"message": MESSAGE, **extra}, format="json")


def decide(client, join_request, decision, **payload):
    return client.post(
        f"/api/v1/join-requests/{join_request['id']}/{decision}/", payload, format="json"
    )


@pytest.fixture
def project(user):
    return make_project(user)


class TestApply:
    def test_member_sends_motivated_request_and_owner_is_notified(
        self, client_for, project, other_user
    ):
        response = apply(client_for(other_user), project)

        assert response.status_code == 201, response.json()
        assert response.json()["status"] == "PENDING"
        notification = Notification.objects.get(recipient=project.owner)
        assert notification.type == "JOIN_REQUEST_RECEIVED"

    def test_short_message_is_refused(self, client_for, project, other_user):
        response = client_for(other_user).post(requests_url(project), {"message": "Salut"})

        assert response.status_code == 400

    def test_no_duplicate_pending_request(self, client_for, project, other_user):
        client = client_for(other_user)
        apply(client, project)

        response = apply(client, project)

        assert response.status_code == 409
        assert response.json()["code"] == "duplicate_request"

    def test_database_forbids_two_pending_requests(self, project, other_user):
        JoinRequest.objects.create(project=project, user=other_user, message=MESSAGE)

        with pytest.raises(IntegrityError):
            JoinRequest.objects.create(project=project, user=other_user, message=MESSAGE)

    def test_members_and_closed_projects_cannot_receive_requests(
        self, client_for, user, other_user
    ):
        project = make_project(user)
        closed = make_project(user, accepts_join_requests=False)
        archived = make_project(user, status=Project.Status.ARCHIVED)

        assert apply(client_for(user), project).json()["code"] == "already_member"
        assert apply(client_for(other_user), closed).json()["code"] == "project_closed"
        assert apply(client_for(other_user), archived).json()["code"] == "project_closed"

    def test_requested_role_must_be_open_and_belong_to_project(
        self, client_for, project, other_user
    ):
        closed_role = RoleNeedFactory(project=project, is_open=False)
        foreign_role = RoleNeedFactory(project=make_project())

        assert (
            apply(client_for(other_user), project, requested_role=str(closed_role.id)).status_code
            == 400
        )
        assert (
            apply(client_for(other_user), project, requested_role=str(foreign_role.id)).status_code
            == 404
        )

    def test_anonymous_cannot_apply(self, api_client, project):
        assert apply(api_client, project).status_code == 401

    def test_requests_are_rate_limited(self, client_for, other_user, monkeypatch):
        monkeypatch.setitem(ScopedWriteThrottle.THROTTLE_RATES, "join_request", "1/hour")
        client = client_for(other_user)

        assert apply(client, make_project()).status_code == 201
        assert apply(client, make_project()).status_code == 429


class TestPrivacyOfRequests:
    def test_only_managers_list_requests(self, client_for, project, other_user):
        apply(client_for(other_user), project)
        contributor = add_member(project).user
        habilitated = add_member(project, role=Role.MANAGER, can_manage_members=True).user
        manager_without_right = add_member(project, role=Role.MANAGER).user

        assert client_for(project.owner).get(requests_url(project)).json()["count"] == 1
        assert client_for(habilitated).get(requests_url(project)).json()["count"] == 1
        assert client_for(contributor).get(requests_url(project)).status_code == 403
        assert client_for(manager_without_right).get(requests_url(project)).status_code == 403

    def test_other_candidates_cannot_read_a_request(self, client_for, project, other_user):
        join_request = apply(client_for(other_user), project).json()
        rival = UserFactory()
        url = f"/api/v1/join-requests/{join_request['id']}/"

        assert client_for(rival).get(url).status_code == 404
        assert client_for(add_member(project).user).get(url).status_code == 404
        assert client_for(other_user).get(url).json()["message"] == MESSAGE
        assert client_for(project.owner).get(url).status_code == 200

    def test_candidate_lists_own_requests(self, client_for, project, other_user):
        apply(client_for(other_user), project)

        assert client_for(other_user).get("/api/v1/join-requests/mine/").json()["count"] == 1
        assert client_for(project.owner).get("/api/v1/join-requests/mine/").json()["count"] == 0

    def test_status_filter(self, client_for, project, other_user):
        apply(client_for(other_user), project)

        response = client_for(project.owner).get(requests_url(project), {"status": "ACCEPTED"})

        assert response.json()["count"] == 0


class TestDecisions:
    def test_accept_creates_member_and_notifies(self, client_for, project, other_user):
        join_request = apply(client_for(other_user), project).json()

        response = decide(
            client_for(project.owner), join_request, "accept", response_message="Bienvenue !"
        )

        assert response.status_code == 200
        assert response.json()["status"] == "ACCEPTED"
        member = ProjectMember.objects.get(project=project, user=other_user, status="ACTIVE")
        assert member.role == Role.CONTRIBUTOR
        assert Notification.objects.filter(
            recipient=other_user, type="JOIN_REQUEST_ACCEPTED"
        ).exists()
        members = client_for(other_user).get(f"/api/v1/projects/{project.slug}/members/").json()
        assert {item["user"]["username"] for item in members["results"]} == {"awa", "kofi"}

    @pytest.mark.parametrize("who", ["candidate", "contributor", "outsider", "admin_user"])
    def test_unauthorized_users_cannot_decide(self, request, client_for, project, other_user, who):
        join_request = apply(client_for(other_user), project).json()
        actor = {
            "candidate": other_user,
            "contributor": add_member(project).user,
            "outsider": UserFactory(),
            "admin_user": request.getfixturevalue("admin_user"),
        }[who]

        for decision in ("accept", "reject"):
            assert decide(client_for(actor), join_request, decision).status_code in {403, 404}
        assert not ProjectMember.objects.filter(project=project, user=other_user).exists()

    def test_only_owner_grants_manager_role(self, client_for, project, other_user):
        habilitated = add_member(project, role=Role.MANAGER, can_manage_members=True).user
        join_request = apply(client_for(other_user), project).json()

        assert (
            decide(client_for(habilitated), join_request, "accept", role="MANAGER").status_code
            == 403
        )
        assert (
            decide(client_for(habilitated), join_request, "accept", role="OBSERVER").status_code
            == 200
        )

    def test_cannot_accept_when_project_is_closed(self, client_for, project, other_user):
        join_request = apply(client_for(other_user), project).json()
        Project.objects.filter(pk=project.pk).update(status=Project.Status.PAUSED)

        response = decide(client_for(project.owner), join_request, "accept")

        assert response.status_code == 409
        assert JoinRequest.objects.get(pk=join_request["id"]).status == "PENDING"
        assert not ProjectMember.objects.filter(project=project, user=other_user).exists()

    def test_decided_request_cannot_be_decided_again(self, client_for, project, other_user):
        join_request = apply(client_for(other_user), project).json()
        owner = client_for(project.owner)
        decide(owner, join_request, "reject")

        assert decide(owner, join_request, "accept").json()["code"] == "invalid_transition"
        assert decide(client_for(other_user), join_request, "withdraw").status_code == 409

    def test_reject_blocks_immediate_reapply_until_allowed(self, client_for, project, other_user):
        candidate, owner = client_for(other_user), client_for(project.owner)
        join_request = apply(candidate, project).json()

        rejected = decide(owner, join_request, "reject", response_message="Profil trop éloigné.")
        assert rejected.json()["response_message"] == "Profil trop éloigné."
        assert Notification.objects.filter(
            recipient=other_user, type="JOIN_REQUEST_REJECTED"
        ).exists()
        assert apply(candidate, project).json()["code"] == "reapply_cooldown"

        assert decide(owner, join_request, "allow-reapply").json()["can_reapply"] is True
        assert apply(candidate, project).status_code == 201

    def test_reapply_possible_after_cooldown(self, client_for, project, other_user):
        join_request = apply(client_for(other_user), project).json()
        decide(client_for(project.owner), join_request, "reject")
        JoinRequest.objects.filter(pk=join_request["id"]).update(
            reviewed_at=timezone.now() - timedelta(days=31)
        )

        assert apply(client_for(other_user), project).status_code == 201

    def test_allow_reapply_only_on_rejected(self, client_for, project, other_user):
        join_request = apply(client_for(other_user), project).json()

        assert decide(client_for(project.owner), join_request, "allow-reapply").status_code == 409
        assert decide(client_for(other_user), join_request, "allow-reapply").status_code == 403

    def test_candidate_withdraws(self, client_for, project, other_user):
        join_request = apply(client_for(other_user), project).json()

        assert decide(client_for(project.owner), join_request, "withdraw").status_code == 403
        assert (
            decide(client_for(other_user), join_request, "withdraw").json()["status"] == "WITHDRAWN"
        )
        assert apply(client_for(other_user), project).status_code == 201

    def test_role_need_closes_when_slots_are_filled(self, client_for, project):
        role = RoleNeedFactory(project=project, slots=1)
        candidate = UserFactory()
        join_request = apply(client_for(candidate), project, requested_role=str(role.id)).json()

        decide(client_for(project.owner), join_request, "accept")

        role.refresh_from_db()
        assert role.is_open is False
        assert ProjectMember.objects.get(user=candidate).title == role.role_name

    def test_database_forbids_two_active_memberships(self, project, other_user):
        add_member(project, other_user)

        with pytest.raises(IntegrityError):
            add_member(project, other_user)
