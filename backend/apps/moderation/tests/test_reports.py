import uuid

import pytest

from apps.community.models import ContentStatus
from apps.community.tests.factories import AnswerFactory, CommentFactory, PostFactory
from apps.moderation.models import Report
from apps.projects.models import Project
from apps.projects.tests.factories import make_project
from common.throttling import ScopedWriteThrottle

pytestmark = pytest.mark.django_db

URL = "/api/v1/reports/"


def report(client, target_type, target_id, reason="SPAM", **extra):
    payload = {"target_type": target_type, "target_id": str(target_id), "reason": reason, **extra}
    return client.post(URL, payload, format="json")


class TestCreateReport:
    @pytest.mark.parametrize(
        ("target_type", "factory"),
        [
            ("POST", lambda: PostFactory()),
            ("COMMENT", lambda: CommentFactory()),
            ("ANSWER", lambda: AnswerFactory()),
            ("PROJECT", lambda: make_project()),
        ],
    )
    def test_member_reports_each_target_type(self, client_for, user, target_type, factory):
        target = factory()

        response = report(client_for(user), target_type, target.pk)

        assert response.status_code == 201, response.json()
        assert response.json()["status"] == "PENDING"

    def test_member_reports_a_profile(self, client_for, user, other_user):
        assert (
            report(client_for(user), "PROFILE", other_user.pk, "IMPERSONATION").status_code == 201
        )

    def test_anonymous_cannot_report(self, api_client):
        assert report(api_client, "POST", PostFactory().pk).status_code == 401

    def test_cannot_report_own_content_or_twice(self, client_for, user):
        own = PostFactory(author=user)
        other = PostFactory()
        client = client_for(user)

        assert report(client, "POST", own.pk).json()["code"] == "self_report"
        assert report(client, "PROFILE", user.pk).json()["code"] == "self_report"
        assert report(client, "POST", other.pk).status_code == 201
        assert report(client, "POST", other.pk).json()["code"] == "duplicate_report"

    def test_other_reason_requires_details(self, client_for, user):
        post = PostFactory()

        missing = report(client_for(user), "POST", post.pk, "OTHER")
        ok = report(
            client_for(user), "POST", post.pk, "OTHER", details="Lien vers un site douteux."
        )

        assert missing.status_code == 400 and "details" in missing.json()["errors"]
        assert ok.status_code == 201

    def test_unknown_or_invisible_targets(self, client_for, user):
        hidden = PostFactory(status=ContentStatus.HIDDEN)
        private = make_project(visibility=Project.Visibility.PRIVATE)
        client = client_for(user)

        assert report(client, "POST", uuid.uuid4()).status_code == 404
        assert report(client, "POST", hidden.pk).status_code == 404
        assert report(client, "PROJECT", private.pk).status_code == 404
        assert report(client, "MESSAGE", uuid.uuid4()).status_code == 404
        assert report(client, "NOPE", uuid.uuid4()).status_code == 400

    def test_reporting_is_rate_limited(self, client_for, user, monkeypatch):
        monkeypatch.setitem(ScopedWriteThrottle.THROTTLE_RATES, "report_create", "1/hour")
        client = client_for(user)

        assert report(client, "POST", PostFactory().pk).status_code == 201
        assert report(client, "POST", PostFactory().pk).status_code == 429

    def test_reporter_lists_own_reports(self, client_for, user, other_user):
        report(client_for(user), "POST", PostFactory().pk)
        report(client_for(other_user), "POST", PostFactory().pk)

        body = client_for(user).get(f"{URL}mine/").json()

        assert body["count"] == 1
        assert Report.objects.count() == 2
