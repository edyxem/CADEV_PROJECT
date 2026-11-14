import pytest
from django.core import mail
from rest_framework.exceptions import NotFound

from apps.accounts.tests.factories import UserFactory
from apps.catalog.tests.factories import TechnologyFactory
from apps.messaging.models import Block, Message
from apps.moderation.services import create_report, take_action
from apps.notifications.models import Notification, NotificationPreference
from apps.notifications.services import notify
from apps.profiles.models import UserSkill
from apps.projects.models import Project
from apps.projects.tests.factories import add_member, make_project
from apps.social.models import Follow
from common.throttling import ScopedWriteThrottle

pytestmark = pytest.mark.django_db

URL = "/api/v1/conversations/"


def start(client, username="kofi", content="Bonjour, ton projet m'intéresse !"):
    return client.post(URL, {"username": username, "content": content})


class TestConversations:
    def test_start_reply_and_read(self, client_for, user, other_user):
        awa, kofi = client_for(user), client_for(other_user)

        created = start(awa)
        conversation_id = created.json()["id"]
        assert created.status_code == 201
        assert created.json()["other"]["username"] == "kofi"
        assert start(awa, content="Second message").json()["id"] == conversation_id

        inbox = kofi.get(URL).json()["results"][0]
        assert inbox["unread_count"] == 2
        assert (
            Notification.objects.filter(recipient=other_user, type="MESSAGE_RECEIVED").count() == 1
        )

        assert (
            kofi.post(
                f"{URL}{conversation_id}/messages/", {"content": "Avec plaisir !"}
            ).status_code
            == 201
        )
        assert kofi.post(f"{URL}{conversation_id}/read/").status_code == 204
        assert kofi.get(f"{URL}{conversation_id}/").json()["unread_count"] == 0
        assert not Notification.objects.filter(recipient=other_user, is_read=False).exists()
        assert awa.get(f"{URL}{conversation_id}/messages/").json()["count"] == 3

    def test_conversations_are_private(self, client_for, user, other_user):
        conversation_id = start(client_for(user)).json()["id"]
        outsider = client_for(UserFactory())

        assert outsider.get(f"{URL}{conversation_id}/").status_code == 404
        assert outsider.get(f"{URL}{conversation_id}/messages/").status_code == 404
        assert (
            outsider.post(f"{URL}{conversation_id}/messages/", {"content": "intrusion"}).status_code
            == 404
        )

    def test_rules(self, client_for, user):
        UserFactory(username="parti", is_active=False)
        client = client_for(user)

        assert start(client, "awa").json()["code"] == "self_message"
        assert start(client, "parti").json()["code"] == "inactive_account"
        assert start(client, "kofi", content="<b></b>").status_code == 400

    @pytest.mark.parametrize(
        "content",
        [
            "Clique ici javascript:alert(1)",
            "Voir ftp://files.example.org/a",
            "https://a.org https://b.org https://c.org https://d.org",
        ],
    )
    def test_malicious_or_spammy_links_are_refused(self, client_for, user, other_user, content):
        assert start(client_for(user), content=content).status_code == 400

    def test_safe_links_are_accepted(self, client_for, user, other_user):
        assert (
            start(client_for(user), content="Doc : https://docs.djangoproject.com/").status_code
            == 201
        )

    def test_messaging_is_rate_limited(self, client_for, user, other_user, monkeypatch):
        monkeypatch.setitem(ScopedWriteThrottle.THROTTLE_RATES, "messaging", "1/hour")
        client = client_for(user)

        assert start(client).status_code == 201
        assert start(client).status_code == 429


class TestBlocking:
    def test_block_prevents_messages_both_ways(self, client_for, user, other_user):
        conversation_id = start(client_for(other_user), "awa").json()["id"]

        blocked = client_for(user).post("/api/v1/blocks/", {"username": "kofi"})

        assert blocked.status_code == 201
        assert (
            client_for(other_user)
            .post(f"{URL}{conversation_id}/messages/", {"content": "Encore moi"})
            .json()["code"]
            == "blocked"
        )
        assert start(client_for(user)).json()["code"] == "blocked"
        assert (
            client_for(user).post("/api/v1/blocks/", {"username": "kofi"}).json()["code"]
            == "already_blocked"
        )
        assert (
            client_for(user).post("/api/v1/blocks/", {"username": "awa"}).json()["code"]
            == "self_block"
        )

        block_id = client_for(user).get("/api/v1/blocks/").json()["results"][0]["id"]
        assert client_for(other_user).delete(f"/api/v1/blocks/{block_id}/").status_code == 404
        assert client_for(user).delete(f"/api/v1/blocks/{block_id}/").status_code == 204
        assert not Block.objects.exists()


class TestReportedMessages:
    def test_participant_reports_and_moderator_hides_only_that_message(
        self, client_for, user, other_user, moderator
    ):
        conversation_id = start(
            client_for(other_user), "awa", content="Envoie-moi ton mot de passe"
        ).json()["id"]
        message = Message.objects.get()

        with pytest.raises(NotFound):  # un tiers ne voit pas le message
            create_report(
                reporter=UserFactory(), target_type="MESSAGE", target_id=message.pk, reason="SCAM"
            )
        report = create_report(
            reporter=user, target_type="MESSAGE", target_id=message.pk, reason="SCAM"
        )
        queue = client_for(moderator).get("/api/v1/moderation/reports/").json()["results"][0]
        assert queue["target"]["excerpt"] == "Envoie-moi ton mot de passe"

        take_action(moderator=moderator, report=report, action="HIDE", reason="Hameçonnage.")

        body = client_for(user).get(f"{URL}{conversation_id}/messages/").json()["results"][0]
        assert body["is_hidden"] is True and body["content"] == "Message masqué par la modération."


class TestDiscovery:
    def test_recommended_developers_and_projects(self, client_for, user, other_user):
        django, react = (
            TechnologyFactory(name="Django", slug="django"),
            TechnologyFactory(name="React", slug="react"),
        )
        UserSkill.objects.create(user=user, technology=django, level="ADVANCED")
        Follow.objects.create(follower=user, target_type="TECHNOLOGY", technology=react)
        UserSkill.objects.create(user=other_user, technology=django, level="EXPERT")
        unrelated = UserFactory()
        open_project = make_project(other_user, name="Projet React ouvert", technologies=[react])
        make_project(
            unrelated, name="Projet fermé React", technologies=[react], accepts_join_requests=False
        )
        mine = make_project(user, name="Mon projet Django", technologies=[django])
        add_member(open_project, UserFactory())

        developers = client_for(user).get("/api/v1/recommendations/developers/").json()["results"]
        projects = client_for(user).get("/api/v1/recommendations/projects/").json()["results"]

        assert [item["username"] for item in developers] == ["kofi"]
        assert [item["slug"] for item in projects] == [open_project.slug]
        assert mine.slug not in {item["slug"] for item in projects}

    def test_recommendations_require_authentication(self, api_client):
        assert api_client.get("/api/v1/recommendations/developers/").status_code == 401


class TestPortfolio:
    def test_owner_manages_portfolio_and_public_view_lists_completed_projects(
        self, client_for, api_client, user
    ):
        TechnologyFactory(name="Flutter", slug="flutter")
        client = client_for(user)
        created = client.post(
            "/api/v1/profiles/me/portfolio/",
            {
                "title": "Application de covoiturage",
                "url": "https://example.org/demo",
                "technologies": ["flutter"],
            },
            format="json",
        )
        project = make_project(user, name="Projet livré")
        Project.objects.filter(pk=project.pk).update(status=Project.Status.COMPLETED)

        body = api_client.get("/api/v1/profiles/awa/portfolio/").json()

        assert created.status_code == 201
        assert body["items"][0]["technologies"] == ["flutter"]
        assert [item["slug"] for item in body["completed_projects"]] == [project.slug]
        assert (
            client.patch(
                f"/api/v1/profiles/me/portfolio/{created.json()['id']}/", {"sort_order": 2}
            ).status_code
            == 200
        )
        assert (
            client.post(
                "/api/v1/profiles/me/portfolio/", {"title": "x", "url": "javascript:x"}
            ).status_code
            == 400
        )

    def test_private_profile_portfolio_and_limit(self, client_for, api_client, user, monkeypatch):
        user.profile.profile_visibility = "PRIVATE"
        user.profile.save()
        monkeypatch.setattr("apps.profiles.views.MAX_PORTFOLIO_ITEMS", 0)

        assert api_client.get("/api/v1/profiles/awa/portfolio/").status_code == 404
        assert client_for(user).get("/api/v1/profiles/awa/portfolio/").status_code == 200
        assert (
            client_for(user)
            .post("/api/v1/profiles/me/portfolio/", {"title": "Trop"})
            .json()["code"]
            == "portfolio_limit"
        )


class TestEmailNotifications:
    def test_opted_in_types_are_emailed_to_verified_addresses(
        self, user, other_user, django_capture_on_commit_callbacks
    ):
        NotificationPreference.objects.create(user=user, email_types=["NEW_FOLLOWER"])
        NotificationPreference.objects.create(
            user=UserFactory(username="nonverif", email_verified=False),
            email_types=["NEW_FOLLOWER"],
        )

        with django_capture_on_commit_callbacks(execute=True):
            notify(user, type="NEW_FOLLOWER", title="kofi vous suit", target_url="/membres/kofi")
            notify(user, type="TASK_ASSIGNED", title="Nouvelle tâche")
            notify(other_user, type="NEW_FOLLOWER", title="Sans préférence")
            notify(
                UserFactory._meta.model.objects.get(username="nonverif"),
                type="NEW_FOLLOWER",
                title="Non vérifié",
            )

        assert [message.to for message in mail.outbox] == [[user.email]]
        assert "/membres/kofi" in mail.outbox[0].body
