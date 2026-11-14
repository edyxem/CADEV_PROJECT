import pytest
from django.core.management import call_command

from apps.accounts.tests.factories import UserFactory
from apps.catalog.tests.factories import TechnologyFactory
from apps.community import services as community
from apps.community.models import AnswerVote, ContentStatus, Post, PostVote
from apps.community.tests.factories import AnswerFactory, PostFactory, QuestionFactory
from apps.notifications.models import Notification
from apps.projects.models import Project, ProjectTask
from apps.projects.tests.factories import TaskFactory, add_member, make_project
from apps.reputation import services
from apps.reputation.models import Achievement, ContributionEvent, Recommendation, UserAchievement

pytestmark = pytest.mark.django_db


def score(user) -> int:
    return services.sync_user(user)


class TestScoring:
    def test_new_account_has_no_points(self, user):
        assert score(user) == 0
        assert not ContributionEvent.objects.exists()

    def test_accepted_answer_and_votes(self, user, other_user):
        question = QuestionFactory(author=other_user)
        answer = AnswerFactory(question=question, author=user)
        community.accept_answer(answer=answer, actor=other_user)
        for voter in UserFactory.create_batch(3):
            AnswerVote.objects.create(user=voter, answer=answer)

        assert score(user) == 15 + 3 * 2
        assert {row["event_type"]: row["count"] for row in services.breakdown(user)} == {
            "ANSWER_ACCEPTED": 1,
            "ANSWER_UPVOTED": 3,
        }

    def test_votes_are_capped_per_object(self, user, monkeypatch):
        monkeypatch.setattr(
            "apps.reputation.services.RULES",
            {
                **services.RULES,
                "POST_UPVOTED": services.RULES["POST_UPVOTED"].__class__(
                    points=1, max_per_object=2
                ),
            },
        )
        post = PostFactory(author=user)
        for voter in UserFactory.create_batch(4):
            PostVote.objects.create(user=voter, post=post)

        assert score(user) == 2

    def test_votes_from_disabled_accounts_do_not_count(self, user):
        post = PostFactory(author=user)
        PostVote.objects.create(user=UserFactory(is_active=False), post=post)

        assert score(user) == 0

    def test_hidden_content_loses_its_points(self, user):
        post = PostFactory(author=user, type=Post.Type.ARTICLE)
        assert score(user) == 5

        post.status = ContentStatus.HIDDEN
        post.save()

        assert score(user) == 0
        assert not ContributionEvent.objects.filter(user=user).exists()

    def test_articles_are_capped_in_total(self, user, monkeypatch):
        monkeypatch.setattr(
            "apps.reputation.services.RULES",
            {
                **services.RULES,
                "ARTICLE_PUBLISHED": services.RULES["ARTICLE_PUBLISHED"].__class__(
                    points=5, max_total=1
                ),
            },
        )
        PostFactory.create_batch(3, author=user, type=Post.Type.ARTICLE)

        assert score(user) == 5

    def test_project_contributions(self, user, other_user):
        project = make_project(other_user)
        add_member(project, user)
        TaskFactory(
            project=project, assignee=user, status="DONE", completed_at="2026-11-01T10:00:00Z"
        )
        TaskFactory(project=project, assignee=user)
        Project.objects.filter(pk=project.pk).update(status=Project.Status.COMPLETED)

        assert score(user) == 3 + 20
        assert score(other_user) == 20

    def test_recompute_is_idempotent(self, user, capsys):
        PostFactory(author=user, type=Post.Type.ARTICLE)

        call_command("recompute_reputation")
        call_command("recompute_reputation")

        assert ContributionEvent.objects.filter(user=user).count() == 1
        assert "Réputation recalculée" in capsys.readouterr().out


class TestSignals:
    def test_score_follows_live_activity(
        self, user, other_user, django_capture_on_commit_callbacks
    ):
        question = QuestionFactory(author=other_user)
        with django_capture_on_commit_callbacks(execute=True):
            answer = community.add_answer(question=question, author=user, content="<p>Solution</p>")
            community.accept_answer(answer=answer, actor=other_user)
            community.vote_answer(answer=answer, user=UserFactory())

        assert services.score_of(user) == 17

        with django_capture_on_commit_callbacks(execute=True):
            community.unaccept_answer(answer=answer, actor=other_user)
            AnswerVote.objects.filter(answer=answer).delete()

        assert services.score_of(user) == 0

    def test_task_and_project_signals(self, user, other_user, django_capture_on_commit_callbacks):
        project = make_project(other_user)
        add_member(project, user)
        with django_capture_on_commit_callbacks(execute=True):
            task = TaskFactory(project=project, assignee=user)
            task.status, task.completed_at = ProjectTask.Status.DONE, "2026-11-01T10:00:00Z"
            task.save()
            project.status = Project.Status.COMPLETED
            project.save()

        assert services.score_of(user) == 23


class TestAchievements:
    def test_badge_awarded_with_notification_and_revoked_when_no_longer_earned(self, user):
        post = PostFactory(author=user, type=Post.Type.ARTICLE)

        score(user)
        assert UserAchievement.objects.filter(user=user, achievement__code="auteur").exists()
        assert Notification.objects.filter(recipient=user, type="ACHIEVEMENT_AWARDED").count() == 1

        post.status = ContentStatus.DELETED
        post.save()
        score(user)
        assert not UserAchievement.objects.filter(user=user).exists()

    def test_default_achievements_exist_and_are_listed(self, api_client):
        assert Achievement.objects.count() == 8

        body = api_client.get("/api/v1/achievements/").json()

        assert {item["code"] for item in body} >= {"premiere-solution", "mentor"}


class TestRecommendations:
    def url(self, username):
        return f"/api/v1/profiles/{username}/recommendations/"

    def test_member_recommends_with_context(
        self, client_for, api_client, user, other_user, django_capture_on_commit_callbacks
    ):
        TechnologyFactory(name="React", slug="react")

        with django_capture_on_commit_callbacks(execute=True):
            response = client_for(user).post(
                self.url("kofi"),
                {
                    "context": "Nous avons livré ensemble le frontend du projet AgriMarché.",
                    "technology": "react",
                },
            )

        assert response.status_code == 201, response.json()
        assert (
            api_client.get(self.url("kofi")).json()["results"][0]["recommender"]["username"]
            == "awa"
        )
        assert services.score_of(other_user) == 5

    def test_rules(self, client_for, user, other_user):
        context = {"context": "Une collaboration sérieuse sur un projet commun réussi."}
        client = client_for(user)

        assert client.post(self.url("awa"), context).json()["code"] == "self_recommendation"
        assert client.post(self.url("kofi"), {"context": "trop court"}).status_code == 400
        assert client.post(self.url("kofi"), context).status_code == 201
        assert client.post(self.url("kofi"), context).json()["code"] == "duplicate_recommendation"

    def test_only_recommender_deletes(self, client_for, user, other_user):
        recommendation = Recommendation.objects.create(
            recommender=user,
            recommended=other_user,
            context="Collaboration sur un projet open source.",
        )
        url = f"/api/v1/recommendations/{recommendation.id}/"

        assert client_for(other_user).delete(url).status_code == 404
        assert client_for(user).delete(url).status_code == 204

    def test_anonymous_cannot_recommend(self, api_client, other_user):
        assert api_client.post(self.url("kofi"), {"context": "x" * 40}).status_code == 401


class TestReputationEndpoint:
    def test_public_reputation(self, api_client, user):
        PostFactory(author=user, type=Post.Type.ARTICLE)
        score(user)

        body = api_client.get("/api/v1/profiles/awa/reputation/").json()

        assert body["score"] == 5
        assert body["breakdown"][0]["points_per_event"] == 5
        assert body["achievements"][0]["code"] == "auteur"
        assert "preuve de compétence" in body["explanation"]

    def test_private_profile_reputation_is_hidden_from_others(
        self, client_for, api_client, user, moderator
    ):
        user.profile.profile_visibility = "PRIVATE"
        user.profile.save()

        assert api_client.get("/api/v1/profiles/awa/reputation/").status_code == 404
        assert client_for(user).get("/api/v1/profiles/awa/reputation/").status_code == 200
        assert client_for(moderator).get("/api/v1/profiles/awa/reputation/").status_code == 200


class TestDashboard:
    def test_dashboard_summarizes_member_activity(self, client_for, user, other_user):
        PostFactory(author=user)
        PostFactory(author=user, status=ContentStatus.DRAFT, published_at=None)
        project = make_project(user)
        TaskFactory(project=project, assignee=user)
        community.add_comment(
            post=PostFactory(author=user), author=other_user, content="<p>Bravo</p>", parent=None
        )

        body = client_for(user).get("/api/v1/me/dashboard/").json()

        assert body["posts"] == 2 and body["drafts"] == 1
        assert body["projects"] == 1 and body["open_tasks"] == 1
        assert body["unread_notifications"] == 1

    def test_dashboard_requires_authentication(self, api_client):
        assert api_client.get("/api/v1/me/dashboard/").status_code == 401


class TestHiddenReputation:
    def test_member_can_hide_reputation_badges_and_recommendations(
        self, client_for, api_client, user, moderator
    ):
        response = client_for(user).patch(
            "/api/v1/profiles/me/", {"show_reputation": False}, format="json"
        )

        assert response.json()["show_reputation"] is False
        assert api_client.get("/api/v1/profiles/awa/reputation/").status_code == 404
        assert api_client.get("/api/v1/profiles/awa/recommendations/").status_code == 404
        assert client_for(user).get("/api/v1/profiles/awa/reputation/").status_code == 200
        assert client_for(moderator).get("/api/v1/profiles/awa/recommendations/").status_code == 200
        assert api_client.get("/api/v1/profiles/awa/").status_code == 200
