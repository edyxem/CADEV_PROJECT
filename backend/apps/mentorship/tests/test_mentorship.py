import pytest

from apps.accounts.tests.factories import UserFactory
from apps.catalog.tests.factories import CategoryFactory
from apps.mentorship.models import MentorProfile, MentorshipRequest
from apps.notifications.models import Notification
from apps.reputation.services import score_of

pytestmark = pytest.mark.django_db

GOAL = "Je souhaite progresser en architecture backend et préparer un entretien."


@pytest.fixture
def mentor(other_user):
    CategoryFactory(name="Backend et API", slug="backend-et-api")
    return MentorProfile.objects.create(
        user=other_user, headline="Architecte backend", languages=["fr"], max_active_mentees=1
    )


def ask(client, username="kofi", goal=GOAL):
    return client.post("/api/v1/mentorship-requests/", {"mentor": username, "goal": goal})


class TestMentorProfiles:
    def test_member_declares_mentoring_and_appears_in_directory(self, client_for, api_client, user):
        CategoryFactory(name="Cybersécurité", slug="cybersecurite")

        response = client_for(user).put(
            "/api/v1/mentors/me/",
            {
                "headline": "Mentor sécurité",
                "domains": ["cybersecurite"],
                "languages": ["fr", "en"],
            },
            format="json",
        )

        assert response.status_code == 200
        assert api_client.get("/api/v1/mentors/", {"domain": "cybersecurite"}).json()["count"] == 1
        assert api_client.get("/api/v1/mentors/", {"language": "en"}).json()["count"] == 1
        assert api_client.get("/api/v1/mentors/awa/").json()["headline"] == "Mentor sécurité"

        client_for(user).put("/api/v1/mentors/me/", {"is_available": False}, format="json")
        assert api_client.get("/api/v1/mentors/").json()["count"] == 0

    def test_my_profile_404_until_declared(self, client_for, user):
        assert client_for(user).get("/api/v1/mentors/me/").status_code == 404


class TestRequests:
    def test_full_mentorship_flow(
        self, client_for, user, other_user, mentor, django_capture_on_commit_callbacks
    ):
        mentee, mentor_client = client_for(user), client_for(other_user)
        request_id = ask(mentee).json()["id"]
        assert Notification.objects.filter(recipient=other_user, type="MENTORSHIP_UPDATE").exists()

        accepted = mentor_client.post(
            f"/api/v1/mentorship-requests/{request_id}/respond/", {"accept": True}
        )
        assert accepted.json()["status"] == "ACCEPTED"

        session = mentee.post(
            f"/api/v1/mentorship-requests/{request_id}/sessions/",
            {"scheduled_at": "2026-12-01T10:00:00Z", "meeting_url": "https://meet.example.org/abc"},
        )
        assert session.status_code == 201, session.json()
        session_id = session.json()["id"]
        assert (
            mentor_client.patch(
                f"/api/v1/mentorship-sessions/{session_id}/", {"status": "COMPLETED"}
            ).json()["status"]
            == "COMPLETED"
        )
        feedback = mentee.post(
            f"/api/v1/mentorship-sessions/{session_id}/feedback/",
            {"rating": 5, "comment": "Très utile"},
        )
        assert feedback.status_code == 201
        assert (
            mentee.post(
                f"/api/v1/mentorship-sessions/{session_id}/feedback/", {"rating": 4}
            ).json()["code"]
            == "duplicate_feedback"
        )
        assert (
            len(mentor_client.get(f"/api/v1/mentorship-sessions/{session_id}/feedback/").json())
            == 1
        )

        with django_capture_on_commit_callbacks(execute=True):
            completed = mentee.post(f"/api/v1/mentorship-requests/{request_id}/complete/")
        assert completed.json()["status"] == "COMPLETED"
        assert score_of(other_user) == 10

    def test_rules(self, client_for, user, other_user, mentor):
        assert ask(client_for(other_user)).json()["code"] == "self_mentorship"
        assert ask(client_for(user), goal="Trop court").status_code == 400
        assert ask(client_for(user), username="inconnu").status_code == 400
        assert ask(client_for(user)).status_code == 201
        assert ask(client_for(user)).json()["code"] == "duplicate_request"

    def test_unavailable_mentor_and_capacity(self, client_for, user, other_user, mentor):
        second_mentee = UserFactory()
        first = ask(client_for(user)).json()["id"]
        second = ask(client_for(second_mentee)).json()["id"]
        mentor_client = client_for(other_user)
        mentor_client.post(f"/api/v1/mentorship-requests/{first}/respond/", {"accept": True})

        assert (
            mentor_client.post(
                f"/api/v1/mentorship-requests/{second}/respond/", {"accept": True}
            ).json()["code"]
            == "mentor_full"
        )
        assert (
            mentor_client.post(
                f"/api/v1/mentorship-requests/{second}/respond/", {"accept": False}
            ).json()["status"]
            == "DECLINED"
        )

        mentor.is_available = False
        mentor.save()
        assert ask(client_for(UserFactory())).json()["code"] == "mentor_unavailable"

    def test_privacy_and_permissions(self, client_for, user, other_user, mentor):
        request_id = ask(client_for(user)).json()["id"]
        outsider = client_for(UserFactory())

        assert outsider.get(f"/api/v1/mentorship-requests/{request_id}/").status_code == 404
        assert (
            client_for(user)
            .post(f"/api/v1/mentorship-requests/{request_id}/respond/", {"accept": True})
            .status_code
            == 403
        )
        assert (
            client_for(user).get("/api/v1/mentorship-requests/", {"role": "mentee"}).json()["count"]
            == 1
        )
        assert (
            client_for(other_user)
            .get("/api/v1/mentorship-requests/", {"role": "mentor"})
            .json()["count"]
            == 1
        )

    def test_sessions_require_active_mentorship(self, client_for, user, mentor):
        request_id = ask(client_for(user)).json()["id"]

        response = client_for(user).post(
            f"/api/v1/mentorship-requests/{request_id}/sessions/",
            {"scheduled_at": "2026-12-01T10:00:00Z"},
        )

        assert response.json()["code"] == "mentorship_not_active"

    def test_feedback_only_after_completed_session_and_cancel(
        self, client_for, user, other_user, mentor
    ):
        request_id = ask(client_for(user)).json()["id"]
        client_for(other_user).post(
            f"/api/v1/mentorship-requests/{request_id}/respond/", {"accept": True}
        )
        session_id = client_for(user).post(
            f"/api/v1/mentorship-requests/{request_id}/sessions/",
            {"scheduled_at": "2026-12-01T10:00:00Z", "meeting_url": "ftp://x"},
        )
        assert session_id.status_code == 400
        session_id = (
            client_for(user)
            .post(
                f"/api/v1/mentorship-requests/{request_id}/sessions/",
                {"scheduled_at": "2026-12-01T10:00:00Z"},
            )
            .json()["id"]
        )

        assert (
            client_for(user)
            .post(f"/api/v1/mentorship-sessions/{session_id}/feedback/", {"rating": 5})
            .json()["code"]
            == "session_not_completed"
        )
        assert (
            client_for(user).get(f"/api/v1/mentorship-sessions/{session_id}/").json()["status"]
            == "PLANNED"
        )
        assert (
            client_for(user)
            .post(f"/api/v1/mentorship-requests/{request_id}/cancel/")
            .json()["status"]
            == "CANCELLED"
        )
        assert MentorshipRequest.objects.get(pk=request_id).status == "CANCELLED"
