import pytest

from apps.accounts.tests.factories import UserFactory
from apps.community import services
from apps.community.models import Answer, AnswerVote, ContentStatus, PostVote
from apps.community.tests.factories import (
    AnswerFactory,
    CommentFactory,
    PostFactory,
    QuestionFactory,
)
from apps.notifications.models import Notification
from common.exceptions import BusinessRuleViolation

pytestmark = pytest.mark.django_db


def post_url(post, suffix=""):
    return f"/api/v1/posts/{post.id}/{suffix}"


class TestComments:
    def test_member_comments_and_author_is_notified(self, client_for, user, other_user):
        post = PostFactory(author=user)

        response = client_for(other_user).post(post_url(post, "comments/"), {"content": "Bravo !"})

        assert response.status_code == 201
        assert response.json()["author"]["username"] == "kofi"
        notification = Notification.objects.get(recipient=user)
        assert notification.type == Notification.Type.COMMENT_CREATED
        assert notification.target_url == f"/publications/{post.id}"

    def test_commenting_own_post_does_not_notify(self, client_for, user):
        post = PostFactory(author=user)

        client_for(user).post(post_url(post, "comments/"), {"content": "Précision"})

        assert not Notification.objects.exists()

    def test_reply_notifies_parent_author(self, client_for, user, other_user):
        post = PostFactory(author=user)
        third = UserFactory(username="zainab")
        parent = CommentFactory(post=post, author=other_user)

        response = client_for(third).post(
            post_url(post, "comments/"), {"content": "D'accord", "parent": str(parent.id)}
        )

        assert response.json()["parent"] == str(parent.id)
        assert set(Notification.objects.values_list("recipient__username", "type")) == {
            ("awa", "COMMENT_CREATED"),
            ("kofi", "COMMENT_REPLY"),
        }

    def test_nesting_is_limited_to_one_level(self, client_for, user):
        post = PostFactory()
        parent = CommentFactory(post=post)
        child = CommentFactory(post=post, parent=parent)
        other_post_comment = CommentFactory()
        client = client_for(user)

        deep = client.post(post_url(post, "comments/"), {"content": "x", "parent": str(child.id)})
        foreign = client.post(
            post_url(post, "comments/"), {"content": "x", "parent": str(other_post_comment.id)}
        )

        assert deep.status_code == 400 and foreign.status_code == 400

    def test_anonymous_reads_but_cannot_comment(self, api_client):
        post = PostFactory()
        CommentFactory(post=post)

        assert api_client.get(post_url(post, "comments/")).json()["count"] == 1
        assert api_client.post(post_url(post, "comments/"), {"content": "x"}).status_code == 401

    def test_removed_comment_with_replies_stays_as_placeholder(self, api_client):
        post = PostFactory()
        parent = CommentFactory(post=post, status=ContentStatus.DELETED)
        CommentFactory(post=post, parent=parent)
        CommentFactory(post=post, status=ContentStatus.HIDDEN)

        results = api_client.get(post_url(post, "comments/")).json()["results"]

        assert len(results) == 2
        placeholder = results[0]
        assert placeholder["is_removed"] is True
        assert placeholder["author"] is None and placeholder["content"] == ""

    def test_author_edits_and_deletes_comment(self, client_for, user, other_user):
        comment = CommentFactory(author=user)
        url = f"/api/v1/comments/{comment.id}/"

        assert client_for(other_user).patch(url, {"content": "pirate"}).status_code == 403
        assert client_for(user).patch(url, {"content": "<p>Corrigé</p>"}).json()["content"] == (
            "<p>Corrigé</p>"
        )
        assert client_for(other_user).delete(url).status_code == 403
        assert client_for(user).delete(url).status_code == 204
        comment.refresh_from_db()
        assert comment.status == ContentStatus.DELETED

    def test_cannot_comment_unpublished_post(self, client_for, user):
        draft = PostFactory(author=user, status=ContentStatus.DRAFT, published_at=None)

        response = client_for(user).post(post_url(draft, "comments/"), {"content": "x"})

        assert response.status_code == 409


class TestPostVotes:
    def test_toggle_and_idempotent_votes(self, client_for, other_user):
        post = PostFactory()
        client = client_for(other_user)
        url = post_url(post, "vote/")

        assert client.post(url).json() == {"voted": True, "vote_count": 1}
        assert client.post(url, {"active": True}, format="json").json()["vote_count"] == 1
        assert client.post(url, {"active": True}, format="json").json()["vote_count"] == 1
        assert client.post(url).json() == {"voted": False, "vote_count": 0}
        assert client.delete(url).json() == {"voted": False, "vote_count": 0}
        assert PostVote.objects.count() == 0

    def test_repeated_requests_never_duplicate_a_vote(self, other_user):
        post = PostFactory()

        for _ in range(5):
            services.vote_post(post=post, user=other_user, active=True)

        assert PostVote.objects.filter(post=post).count() == 1

    def test_self_vote_and_anonymous_vote_are_refused(self, client_for, api_client, user):
        post = PostFactory(author=user)

        assert client_for(user).post(post_url(post, "vote/")).status_code == 409
        assert api_client.post(post_url(post, "vote/")).status_code == 401

    def test_counter_matches_stored_votes(self, client_for, api_client):
        post = PostFactory()
        voters = UserFactory.create_batch(3)
        for voter in voters:
            client_for(voter).post(post_url(post, "vote/"))

        body = client_for(voters[0]).get(post_url(post)).json()

        assert body["vote_count"] == PostVote.objects.filter(post=post).count() == 3
        assert body["has_voted"] is True
        assert api_client.get(post_url(post)).json()["has_voted"] is False

    def test_first_vote_reaches_a_milestone_notification(self, other_user):
        post = PostFactory()

        services.vote_post(post=post, user=other_user)

        assert Notification.objects.get(recipient=post.author).type == "VOTE_MILESTONE"

    def test_cannot_vote_on_hidden_post(self, other_user):
        post = PostFactory(status=ContentStatus.HIDDEN)

        with pytest.raises(BusinessRuleViolation):
            services.vote_post(post=post, user=other_user)


class TestAnswers:
    def test_member_answers_and_question_author_is_notified(self, client_for, user, other_user):
        question = QuestionFactory(author=user)

        response = client_for(other_user).post(
            f"/api/v1/questions/{question.id}/answers/",
            {"content": "<p>Utilisez select_related.</p>"},
        )

        assert response.status_code == 201
        assert response.json()["vote_count"] == 0
        assert Notification.objects.get(recipient=user).type == "ANSWER_CREATED"

    def test_answers_only_on_questions(self, client_for, user):
        discussion = PostFactory()

        response = client_for(user).post(
            f"/api/v1/questions/{discussion.id}/answers/", {"content": "x"}
        )

        assert response.status_code == 404
        with pytest.raises(BusinessRuleViolation):
            services.add_answer(question=discussion, author=user, content="<p>x</p>")

    def test_anonymous_cannot_answer_or_vote(self, api_client):
        answer = AnswerFactory()

        assert (
            api_client.post(
                f"/api/v1/questions/{answer.question_id}/answers/", {"content": "x"}
            ).status_code
            == 401
        )
        assert api_client.post(f"/api/v1/answers/{answer.id}/vote/").status_code == 401

    def test_answers_are_sorted_accepted_first_then_votes(self, api_client, user, other_user):
        question = QuestionFactory()
        low = AnswerFactory(question=question)
        high = AnswerFactory(question=question)
        accepted = AnswerFactory(question=question)
        AnswerFactory(question=question, status=ContentStatus.HIDDEN)
        AnswerVote.objects.create(user=user, answer=high)
        AnswerVote.objects.create(user=other_user, answer=high)
        services.accept_answer(answer=accepted, actor=question.author)

        results = api_client.get(f"/api/v1/questions/{question.id}/answers/").json()["results"]
        recent = api_client.get(
            f"/api/v1/questions/{question.id}/answers/", {"ordering": "recent"}
        ).json()["results"]

        assert [item["id"] for item in results] == [str(accepted.id), str(high.id), str(low.id)]
        assert recent[0]["id"] == str(accepted.id)

    def test_deleting_an_answer_keeps_the_others(self, client_for, api_client, user):
        question = QuestionFactory()
        mine = AnswerFactory(question=question, author=user)
        AnswerFactory(question=question)

        assert client_for(user).delete(f"/api/v1/answers/{mine.id}/").status_code == 204

        assert api_client.get(f"/api/v1/questions/{question.id}/answers/").json()["count"] == 1
        assert api_client.get(f"/api/v1/posts/{question.id}/").json()["answer_count"] == 1

    def test_author_edits_answer(self, client_for, user, other_user):
        answer = AnswerFactory(author=user)
        url = f"/api/v1/answers/{answer.id}/"

        assert client_for(other_user).patch(url, {"content": "pirate"}).status_code == 403
        assert client_for(user).patch(url, {"content": "<p>Mise à jour</p>"}).status_code == 200
        assert client_for(user).get(url).json()["content"] == "<p>Mise à jour</p>"

    def test_answer_votes(self, client_for, other_user):
        answer = AnswerFactory()
        url = f"/api/v1/answers/{answer.id}/vote/"
        client = client_for(other_user)

        assert client.post(url).json() == {"voted": True, "vote_count": 1}
        assert client.delete(url).json() == {"voted": False, "vote_count": 0}
        assert client_for(answer.author).post(url).status_code == 409


class TestAcceptAnswer:
    def accept(self, client, answer, method="post"):
        return getattr(client, method)(f"/api/v1/answers/{answer.id}/accept/")

    def test_question_author_accepts_and_answerer_is_notified(self, client_for, user, other_user):
        answer = AnswerFactory(question=QuestionFactory(author=user), author=other_user)

        response = self.accept(client_for(user), answer)

        assert response.status_code == 200
        assert response.json()["is_accepted"] is True
        assert Notification.objects.get(recipient=other_user).type == "ANSWER_ACCEPTED"
        question_view = client_for(user).get(f"/api/v1/posts/{answer.question_id}/").json()
        assert question_view["has_accepted_answer"] is True

    @pytest.mark.parametrize("who", ["other_user", "moderator", "admin_user"])
    def test_only_question_author_can_accept(self, request, client_for, user, who):
        answer = AnswerFactory(question=QuestionFactory(author=user))

        response = self.accept(client_for(request.getfixturevalue(who)), answer)

        assert response.status_code == 403
        assert (
            self.accept(client_for(request.getfixturevalue(who)), answer, "delete").status_code
            == 403
        )

    def test_cannot_accept_own_answer(self, client_for, user):
        answer = AnswerFactory(question=QuestionFactory(author=user), author=user)

        response = self.accept(client_for(user), answer)

        assert response.status_code == 409
        assert response.json()["code"] == "self_accept"

    def test_only_one_accepted_answer(self, client_for, user):
        question = QuestionFactory(author=user)
        first, second = AnswerFactory(question=question), AnswerFactory(question=question)
        client = client_for(user)

        self.accept(client, first)
        self.accept(client, second)
        self.accept(client, second)

        assert list(Answer.all_objects.filter(is_accepted=True)) == [second]

    def test_unaccept(self, client_for, user):
        answer = AnswerFactory(question=QuestionFactory(author=user))
        client = client_for(user)
        self.accept(client, answer)

        response = self.accept(client, answer, "delete")

        assert response.json()["is_accepted"] is False

    def test_removed_answer_cannot_be_accepted_and_loses_acceptance(self, user):
        question = QuestionFactory(author=user)
        hidden = AnswerFactory(question=question, status=ContentStatus.HIDDEN)
        accepted = AnswerFactory(question=question)
        services.accept_answer(answer=accepted, actor=user)

        with pytest.raises(BusinessRuleViolation):
            services.accept_answer(answer=hidden, actor=user)

        services.delete_answer(answer=accepted, actor=accepted.author)
        accepted.refresh_from_db()
        assert accepted.is_accepted is False


class TestModerationTransitions:
    def test_moderator_hides_and_restores(self, moderator):
        post = PostFactory()

        assert services.moderate_status(post, target=ContentStatus.HIDDEN, actor=moderator) == (
            ContentStatus.PUBLISHED
        )
        services.moderate_status(post, target=ContentStatus.PUBLISHED, actor=moderator)
        post.refresh_from_db()
        assert post.status == ContentStatus.PUBLISHED

    def test_member_cannot_moderate(self, other_user):
        from rest_framework.exceptions import PermissionDenied

        with pytest.raises(PermissionDenied):
            services.moderate_status(PostFactory(), target=ContentStatus.HIDDEN, actor=other_user)

    def test_only_admin_restores_deleted_content(self, moderator, admin_user):
        from rest_framework.exceptions import PermissionDenied

        post = PostFactory(status=ContentStatus.DELETED)

        with pytest.raises(PermissionDenied):
            services.moderate_status(post, target=ContentStatus.PUBLISHED, actor=moderator)
        services.moderate_status(post, target=ContentStatus.PUBLISHED, actor=admin_user)
        assert post.status == ContentStatus.PUBLISHED

    def test_forbidden_transitions(self, moderator):
        from common.exceptions import InvalidTransition

        draft = PostFactory(status=ContentStatus.DRAFT, published_at=None)
        published = PostFactory()

        with pytest.raises(BusinessRuleViolation):
            services.moderate_status(draft, target=ContentStatus.HIDDEN, actor=moderator)
        with pytest.raises(InvalidTransition):
            services.moderate_status(published, target=ContentStatus.PUBLISHED, actor=moderator)

    def test_restoring_a_never_published_post_sets_its_date(self, admin_user):
        post = PostFactory(status=ContentStatus.DRAFT, published_at=None)
        services._set_status(post, ContentStatus.DELETED)

        services.moderate_status(post, target=ContentStatus.PUBLISHED, actor=admin_user)

        assert post.published_at is not None
