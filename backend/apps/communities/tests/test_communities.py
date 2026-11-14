import pytest

from apps.accounts.tests.factories import UserFactory
from apps.catalog.tests.factories import CategoryFactory, CountryFactory
from apps.communities.models import Community, CommunityMembership
from apps.community.models import Post
from apps.moderation.models import AuditLog
from apps.moderation.services import take_action
from apps.notifications.models import Notification

pytestmark = pytest.mark.django_db

URL = "/api/v1/communities/"


@pytest.fixture
def community(client_for, user):
    CountryFactory(code="SN", name="Sénégal")
    response = client_for(user).post(
        URL,
        {
            "name": "Devs de Dakar",
            "kind": "CITY",
            "description": "Communauté des développeurs de Dakar.",
            "country": "sn",
            "city": "Dakar",
        },
    )
    assert response.status_code == 201, response.json()
    return Community.objects.get(slug=response.json()["slug"])


def post_payload(**extra):
    CategoryFactory(name="Projets et hackathons", slug="projets-et-hackathons")
    data = {
        "title": "Meetup mensuel des développeurs",
        "content": "<p>Qui vient samedi ?</p>",
        "category": "projets-et-hackathons",
    }
    data.update(extra)
    return data


class TestCommunityLifecycle:
    def test_creator_becomes_leader(self, client_for, api_client, user, community):
        body = client_for(user).get(f"{URL}{community.slug}/").json()

        assert body["my_role"] == "LEADER"
        assert body["member_count"] == 1
        assert api_client.get(URL, {"kind": "CITY", "country": "SN"}).json()["count"] == 1
        assert api_client.get(URL, {"q": "dakar"}).json()["count"] == 1

    def test_join_leave_and_last_leader_rule(self, client_for, user, other_user, community):
        member = client_for(other_user)

        assert member.post(f"{URL}{community.slug}/join/").status_code == 201
        assert member.post(f"{URL}{community.slug}/join/").json()["code"] == "already_member"
        assert (
            client_for(user).post(f"{URL}{community.slug}/leave/").json()["code"] == "last_leader"
        )
        assert member.post(f"{URL}{community.slug}/leave/").status_code == 204
        assert member.post(f"{URL}{community.slug}/leave/").json()["code"] == "not_member"

    def test_only_leaders_edit_and_manage(self, client_for, user, other_user, community):
        client_for(other_user).post(f"{URL}{community.slug}/join/")
        membership = CommunityMembership.objects.get(community=community, user=other_user)

        assert (
            client_for(other_user).patch(f"{URL}{community.slug}/", {"rules": "x"}).status_code
            == 403
        )
        assert (
            client_for(user)
            .patch(f"{URL}{community.slug}/", {"rules": "Bienveillance."})
            .json()["rules"]
            == "Bienveillance."
        )
        promoted = client_for(user).patch(
            f"{URL}{community.slug}/members/{membership.id}/", {"role": "LEADER"}
        )
        assert promoted.json()["role"] == "LEADER"
        assert client_for(user).post(f"{URL}{community.slug}/leave/").status_code == 204

    def test_ban_is_logged_and_prevents_rejoining(self, client_for, user, other_user, community):
        client_for(other_user).post(f"{URL}{community.slug}/join/")
        membership = CommunityMembership.objects.get(community=community, user=other_user)

        client_for(user).patch(f"{URL}{community.slug}/members/{membership.id}/", {"ban": True})

        assert AuditLog.objects.filter(action="community.ban").exists()
        assert (
            client_for(other_user).post(f"{URL}{community.slug}/join/").json()["code"] == "banned"
        )

    def test_leader_cannot_manage_self(self, client_for, user, community):
        own = CommunityMembership.objects.get(community=community, user=user)

        response = client_for(user).patch(
            f"{URL}{community.slug}/members/{own.id}/", {"role": "MEMBER"}
        )

        assert response.json()["code"] == "self_management"


class TestCommunityPosts:
    def test_only_members_publish_in_a_community(self, client_for, user, other_user, community):
        payload = post_payload(community=community.slug)

        assert (
            client_for(other_user).post("/api/v1/posts/", payload, format="json").status_code == 403
        )
        response = client_for(user).post("/api/v1/posts/", payload, format="json")

        assert response.status_code == 201
        assert response.json()["community"] == community.slug
        assert client_for(other_user).get(f"{URL}{community.slug}/posts/").json()["count"] == 1

    def test_local_moderation_is_logged_and_notified(self, client_for, user, other_user, community):
        client_for(other_user).post(f"{URL}{community.slug}/join/")
        post_id = (
            client_for(other_user)
            .post("/api/v1/posts/", post_payload(community=community.slug), format="json")
            .json()["id"]
        )
        url = f"{URL}{community.slug}/posts/{post_id}/moderate/"

        assert client_for(other_user).post(url, {"reason": "Hors sujet."}).status_code == 403
        assert (
            client_for(user).post(url, {"reason": "Hors sujet pour la communauté."}).status_code
            == 200
        )

        assert client_for(user).get(f"{URL}{community.slug}/posts/").json()["count"] == 0
        assert (
            client_for(user).get("/api/v1/posts/").json()["count"] == 1
        )  # reste visible dans le fil général
        assert AuditLog.objects.filter(action="community.post_hide").exists()
        assert Notification.objects.filter(recipient=other_user, type="MODERATION_ACTION").exists()
        client_for(user).post(url, {"hidden": False, "reason": "Rétabli après échange."})
        assert Post.all_objects.get(pk=post_id).community_hidden is False

    def test_moderating_a_post_from_another_community_is_404(self, client_for, user, community):
        foreign = Post.all_objects.create(
            author=UserFactory(), title="Publication ailleurs", content="<p>x</p>", status="DRAFT"
        )

        response = client_for(user).post(
            f"{URL}{community.slug}/posts/{foreign.id}/moderate/", {"reason": "Test local."}
        )

        assert response.status_code == 404


class TestGlobalModeration:
    def test_hidden_community_disappears(self, client_for, api_client, user, moderator, community):
        take_action(
            moderator=moderator,
            action="HIDE",
            reason="Spam répété.",
            target_type="COMMUNITY",
            target_id=community.pk,
        )

        assert api_client.get(f"{URL}{community.slug}/").status_code == 404
        assert client_for(moderator).get(f"{URL}{community.slug}/").status_code == 200
        assert client_for(UserFactory()).post(f"{URL}{community.slug}/join/").status_code == 404
