from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.accounts.tests.factories import DEFAULT_PASSWORD, UserFactory
from apps.community.models import ContentStatus, Post
from apps.community.tests.factories import CommentFactory, PostFactory
from apps.moderation.models import AuditLog, ModerationAction
from apps.moderation.services import create_report
from apps.notifications.models import Notification
from apps.projects.tests.factories import make_project

pytestmark = pytest.mark.django_db

QUEUE = "/api/v1/moderation/reports/"
ACTIONS = "/api/v1/moderation/actions/"


@pytest.fixture
def reported_post(user):
    post = PostFactory(title="Gagnez 1000 euros par jour sans effort")
    return post, create_report(reporter=user, target_type="POST", target_id=post.pk, reason="SCAM")


def act(client, report, action, reason="Contenu frauduleux signalé.", **extra):
    return client.post(
        f"{QUEUE}{report.pk}/action/", {"action": action, "reason": reason, **extra}, format="json"
    )


class TestQueueAccess:
    @pytest.mark.parametrize("who", ["user", "other_user"])
    def test_members_cannot_access_moderation(self, request, client_for, who, reported_post):
        client = client_for(request.getfixturevalue(who))

        assert client.get(QUEUE).status_code == 403
        assert client.get(ACTIONS).status_code == 403
        assert client.get("/api/v1/moderation/stats/").status_code == 403

    def test_anonymous_is_rejected(self, api_client):
        assert api_client.get(QUEUE).status_code == 401

    def test_moderator_sees_open_reports_with_target_preview(
        self, client_for, moderator, reported_post
    ):
        post, _ = reported_post

        body = client_for(moderator).get(QUEUE).json()

        item = body["results"][0]
        assert body["count"] == 1
        assert item["target"]["title"] == post.title
        assert item["target_author"]["username"] == post.author.username
        assert item["reporter"] == "awa"
        assert item["can_handle"] is True
        assert item["open_reports_on_target"] == 1

    def test_queue_filters(self, client_for, moderator, reported_post):
        client = client_for(moderator)

        assert client.get(QUEUE, {"status": "CLOSED"}).json()["count"] == 0
        assert client.get(QUEUE, {"status": "ALL"}).json()["count"] == 1
        assert client.get(QUEUE, {"target_type": "COMMENT"}).json()["count"] == 0
        assert client.get(QUEUE, {"reason": "SCAM"}).json()["count"] == 1

    def test_audit_log_is_admin_only(self, client_for, moderator, admin_user):
        assert client_for(moderator).get("/api/v1/moderation/audit-logs/").status_code == 403
        assert client_for(admin_user).get("/api/v1/moderation/audit-logs/").status_code == 200

    def test_stats(self, client_for, moderator, reported_post):
        body = client_for(moderator).get("/api/v1/moderation/stats/").json()

        assert body["open_reports"] == 1
        assert body["published_posts"] == 1


class TestWorkflow:
    def test_claim_hide_close_with_full_traceability(
        self, client_for, api_client, moderator, reported_post
    ):
        post, report = reported_post
        client = client_for(moderator)

        claimed = client.post(f"{QUEUE}{report.pk}/claim/").json()
        assert claimed["status"] == "REVIEWING" and claimed["assigned_to"] == moderator.username

        response = act(client, report, "HIDE")
        assert response.status_code == 200, response.json()
        assert response.json()["status"] == "ACTION_TAKEN"

        post.refresh_from_db()
        assert post.status == ContentStatus.HIDDEN
        assert api_client.get(f"/api/v1/posts/{post.pk}/").status_code == 404

        record = ModerationAction.objects.get()
        assert (record.moderator, record.action_type, record.previous_state, record.new_state) == (
            moderator,
            "HIDE",
            "PUBLISHED",
            "HIDDEN",
        )
        assert record.reason == "Contenu frauduleux signalé."
        assert AuditLog.objects.filter(action="moderation.hide", actor=moderator).exists()

        notification = Notification.objects.get(recipient=post.author, type="MODERATION_ACTION")
        assert "awa" not in notification.title + notification.message

        closed = client.post(f"{QUEUE}{report.pk}/close/")
        assert closed.json()["status"] == "CLOSED"
        assert act(client, report, "HIDE").json()["code"] == "report_closed"

    def test_no_action_rejects_the_report(self, client_for, moderator, reported_post):
        post, report = reported_post

        response = act(client_for(moderator), report, "NO_ACTION", reason="Signalement non fondé.")

        assert response.json()["status"] == "REJECTED"
        post.refresh_from_db()
        assert post.status == ContentStatus.PUBLISHED

    def test_resolving_action_closes_other_open_reports(
        self, client_for, moderator, reported_post, other_user
    ):
        post, report = reported_post
        second = create_report(
            reporter=other_user, target_type="POST", target_id=post.pk, reason="SPAM"
        )

        act(client_for(moderator), report, "DELETE")

        second.refresh_from_db()
        assert second.status == "ACTION_TAKEN"

    def test_moderator_cannot_handle_own_report(self, client_for, moderator):
        post = PostFactory()
        own = create_report(
            reporter=moderator, target_type="POST", target_id=post.pk, reason="SPAM"
        )
        client = client_for(moderator)

        assert client.post(f"{QUEUE}{own.pk}/claim/").status_code == 403
        assert act(client, own, "HIDE").status_code == 403
        assert client.get(QUEUE).json()["results"][0]["can_handle"] is False

    def test_moderator_cannot_moderate_own_content(self, client_for, moderator, user):
        post = PostFactory(author=moderator)
        report = create_report(reporter=user, target_type="POST", target_id=post.pk, reason="SPAM")

        assert act(client_for(moderator), report, "HIDE").status_code == 403

    def test_claim_conflict_between_moderators(self, client_for, moderator, reported_post):
        _, report = reported_post
        other_moderator = UserFactory(role=User.Role.MODERATOR)
        client_for(moderator).post(f"{QUEUE}{report.pk}/claim/")

        response = client_for(other_moderator).post(f"{QUEUE}{report.pk}/claim/")

        assert response.json()["code"] == "already_claimed"

    def test_forbidden_report_transition(self, client_for, moderator, reported_post):
        _, report = reported_post

        assert (
            client_for(moderator).post(f"{QUEUE}{report.pk}/close/").json()["code"]
            == "invalid_transition"
        )

    def test_invalid_action_payloads(self, client_for, moderator, reported_post):
        _, report = reported_post
        client = client_for(moderator)

        assert act(client, report, "SUSPEND").status_code == 400
        assert act(client, report, "HIDE", reason="x").status_code == 400
        assert act(client, report, "TELEPORT").status_code == 400

    def test_unsupported_action_for_target(self, client_for, moderator, user, other_user):
        report = create_report(
            reporter=user, target_type="PROFILE", target_id=other_user.pk, reason="SPAM"
        )

        assert act(client_for(moderator), report, "HIDE").json()["code"] == "unsupported_action"


class TestAccountSanctions:
    @pytest.fixture
    def profile_report(self, user, other_user):
        return create_report(
            reporter=user, target_type="PROFILE", target_id=other_user.pk, reason="HARASSMENT"
        )

    def test_suspension_disables_login_then_expires(
        self, client_for, api_client, moderator, other_user, profile_report
    ):
        response = act(client_for(moderator), profile_report, "SUSPEND", duration_days=7)

        assert response.status_code == 200
        other_user.refresh_from_db()
        assert other_user.is_suspended and not other_user.is_active
        login = api_client.post(
            "/api/v1/auth/login/", {"identifier": "kofi", "password": DEFAULT_PASSWORD}
        )
        assert login.json()["code"] == "account_suspended"
        assert Notification.objects.filter(recipient=other_user, type="MODERATION_ACTION").exists()

        User.objects.filter(pk=other_user.pk).update(
            suspended_until=timezone.now() - timedelta(minutes=1)
        )
        assert (
            api_client.post(
                "/api/v1/auth/login/", {"identifier": "kofi", "password": DEFAULT_PASSWORD}
            ).status_code
            == 200
        )

    def test_unsuspend(self, client_for, moderator, other_user, profile_report):
        client = client_for(moderator)
        act(client, profile_report, "SUSPEND", duration_days=3)

        response = client.post(
            ACTIONS,
            {
                "target_type": "PROFILE",
                "target_id": str(other_user.pk),
                "action": "UNSUSPEND",
                "reason": "Erreur de modération.",
            },
            format="json",
        )

        assert response.status_code == 201
        other_user.refresh_from_db()
        assert other_user.is_active and not other_user.is_suspended
        again = client.post(
            ACTIONS,
            {
                "target_type": "PROFILE",
                "target_id": str(other_user.pk),
                "action": "UNSUSPEND",
                "reason": "Encore une fois.",
            },
            format="json",
        )
        assert again.json()["code"] == "not_suspended"

    def test_ban_is_reserved_to_admins(
        self, client_for, moderator, admin_user, other_user, profile_report
    ):
        assert act(client_for(moderator), profile_report, "BAN").status_code == 403

        assert act(client_for(admin_user), profile_report, "BAN").status_code == 200
        other_user.refresh_from_db()
        assert other_user.is_banned and not other_user.is_active

        unban = client_for(admin_user).post(
            ACTIONS,
            {
                "target_type": "PROFILE",
                "target_id": str(other_user.pk),
                "action": "UNBAN",
                "reason": "Appel accepté.",
            },
            format="json",
        )
        assert unban.status_code == 201
        other_user.refresh_from_db()
        assert other_user.is_active and not other_user.is_banned

    def test_hierarchy_of_sanctions(self, client_for, moderator, admin_user, user):
        other_moderator = UserFactory(role=User.Role.MODERATOR)
        mod_report = create_report(
            reporter=user, target_type="PROFILE", target_id=other_moderator.pk, reason="SPAM"
        )
        admin_report = create_report(
            reporter=user, target_type="PROFILE", target_id=admin_user.pk, reason="SPAM"
        )

        assert act(client_for(moderator), mod_report, "SUSPEND", duration_days=1).status_code == 403
        assert (
            act(client_for(admin_user), mod_report, "SUSPEND", duration_days=1).status_code == 200
        )
        assert (
            act(client_for(moderator), admin_report, "SUSPEND", duration_days=1).status_code == 403
        )

    def test_suspending_a_banned_account_is_refused(
        self, client_for, admin_user, other_user, profile_report
    ):
        act(client_for(admin_user), profile_report, "BAN")

        response = client_for(admin_user).post(
            ACTIONS,
            {
                "target_type": "PROFILE",
                "target_id": str(other_user.pk),
                "action": "SUSPEND",
                "reason": "Double peine.",
                "duration_days": 2,
            },
            format="json",
        )

        assert response.json()["code"] == "already_banned"


class TestDirectActionsAndRestore:
    def direct(self, client, target_type, target_id, action, reason="Décision de modération."):
        return client.post(
            ACTIONS,
            {
                "target_type": target_type,
                "target_id": str(target_id),
                "action": action,
                "reason": reason,
            },
            format="json",
        )

    def test_moderator_restores_hidden_content(self, client_for, moderator):
        comment = CommentFactory(status=ContentStatus.HIDDEN)

        assert (
            self.direct(client_for(moderator), "COMMENT", comment.pk, "RESTORE").status_code == 201
        )
        comment.refresh_from_db()
        assert comment.status == ContentStatus.PUBLISHED

    def test_only_admin_restores_deleted_content(self, client_for, moderator, admin_user):
        post = PostFactory(status=ContentStatus.DELETED)

        assert self.direct(client_for(moderator), "POST", post.pk, "RESTORE").status_code == 403
        assert self.direct(client_for(admin_user), "POST", post.pk, "RESTORE").status_code == 201
        assert Post.all_objects.get(pk=post.pk).status == ContentStatus.PUBLISHED

    def test_no_action_requires_a_report(self, client_for, moderator):
        response = self.direct(client_for(moderator), "POST", PostFactory().pk, "NO_ACTION")

        assert response.json()["code"] == "report_required"

    def test_project_hide_and_restore(self, client_for, api_client, moderator):
        project = make_project()
        client = client_for(moderator)

        assert self.direct(client, "PROJECT", project.pk, "HIDE").status_code == 201
        assert api_client.get(f"/api/v1/projects/{project.slug}/").status_code == 404
        assert (
            self.direct(client, "PROJECT", project.pk, "HIDE").json()["code"]
            == "invalid_transition"
        )
        assert self.direct(client, "PROJECT", project.pk, "RESTORE").status_code == 201
        assert api_client.get(f"/api/v1/projects/{project.slug}/").status_code == 200

    def test_warning_only_notifies(self, client_for, moderator):
        post = PostFactory()

        assert self.direct(client_for(moderator), "POST", post.pk, "WARNING").status_code == 201
        post.refresh_from_db()
        assert post.status == ContentStatus.PUBLISHED
        assert (
            Notification.objects.get(recipient=post.author).title
            == "Avertissement de la modération"
        )

    def test_unknown_target(self, client_for, moderator):
        import uuid

        assert self.direct(client_for(moderator), "POST", uuid.uuid4(), "HIDE").status_code == 404

    def test_action_history_filters(self, client_for, moderator):
        post = PostFactory()
        self.direct(client_for(moderator), "POST", post.pk, "HIDE")

        response = client_for(moderator).get(
            ACTIONS, {"target_type": "POST", "target_id": str(post.pk)}
        )

        assert response.json()["count"] == 1
        assert response.json()["results"][0]["moderator"] == moderator.username
        assert client_for(moderator).get(f"{QUEUE}?status=ALL").status_code == 200


class TestDjangoAdmin:
    @pytest.fixture
    def admin_client(self, client, admin_user):
        client.force_login(admin_user)
        return client

    def test_member_cannot_reach_admin(self, client, user):
        client.force_login(user)

        assert client.get("/admin/").status_code == 302

    def test_admin_hides_and_restores_content_with_journal(self, admin_client):
        post = PostFactory()
        url = "/admin/community/post/"

        admin_client.post(url, {"action": "hide_selection", "_selected_action": [post.pk]})
        post.refresh_from_db()
        assert post.status == ContentStatus.HIDDEN
        admin_client.post(url, {"action": "restore_selection", "_selected_action": [post.pk]})
        post.refresh_from_db()
        assert post.status == ContentStatus.PUBLISHED
        assert ModerationAction.objects.count() == 2

    def test_admin_processes_reports(self, admin_client, reported_post):
        post, report = reported_post
        second_post = PostFactory()
        second = create_report(
            reporter=UserFactory(), target_type="POST", target_id=second_post.pk, reason="SPAM"
        )

        admin_client.post(
            "/admin/moderation/report/",
            {"action": "hide_reported_content", "_selected_action": [report.pk]},
        )
        admin_client.post(
            "/admin/moderation/report/",
            {"action": "reject_reports", "_selected_action": [second.pk, report.pk]},
        )

        report.refresh_from_db()
        second.refresh_from_db()
        assert report.status == "ACTION_TAKEN"
        assert second.status == "REJECTED"

    def test_role_change_in_admin_is_audited(self, admin_client, user):
        admin_client.post(
            "/admin/accounts/user/",
            {"action": "deactivate_accounts", "_selected_action": [user.pk]},
        )
        admin_client.post(
            "/admin/accounts/user/",
            {"action": "reactivate_accounts", "_selected_action": [user.pk]},
        )

        assert set(AuditLog.objects.values_list("action", flat=True)) == {
            "account.admin_deactivate",
            "account.admin_reactivate",
        }

    def test_admin_changelists_render(self, admin_client, reported_post):
        for path in (
            "/admin/moderation/report/",
            "/admin/moderation/moderationaction/",
            "/admin/moderation/auditlog/",
            "/admin/community/post/",
            "/admin/projects/project/",
            "/admin/profiles/developerprofile/",
            "/admin/catalog/technology/",
            "/admin/notifications/notification/",
            "/admin/accounts/user/",
        ):
            assert admin_client.get(path).status_code == 200, path
