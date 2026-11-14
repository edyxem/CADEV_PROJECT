"""Recalcul incrémental : chaque changement de donnée source resynchronise les membres concernés.

Le recalcul a lieu après validation de la transaction ; ``recompute_reputation``
reste disponible pour tout reconstruire.
"""

from typing import Any

from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.community.models import Answer, AnswerVote, Post, PostVote
from apps.projects.models import Project, ProjectMember, ProjectTask

from .models import Recommendation


def _later(*users: Any) -> None:
    def run() -> None:
        from .services import sync_users

        sync_users(users)

    transaction.on_commit(run)


@receiver([post_save, post_delete], sender=AnswerVote, dispatch_uid="reputation.answer_vote")
def _answer_vote(sender: Any, instance: AnswerVote, **kwargs: Any) -> None:
    answer = Answer.all_objects.filter(pk=instance.answer_id).select_related("author").first()
    if answer is not None:
        _later(answer.author)


@receiver([post_save, post_delete], sender=PostVote, dispatch_uid="reputation.post_vote")
def _post_vote(sender: Any, instance: PostVote, **kwargs: Any) -> None:
    post = Post.all_objects.filter(pk=instance.post_id).select_related("author").first()
    if post is not None:
        _later(post.author)


@receiver(post_save, sender=Answer, dispatch_uid="reputation.answer")
def _answer(sender: Any, instance: Answer, **kwargs: Any) -> None:
    _later(instance.author)


@receiver(post_save, sender=Post, dispatch_uid="reputation.post")
def _post(sender: Any, instance: Post, **kwargs: Any) -> None:
    # Un masquage modifie aussi la valeur des votes et réponses liés.
    authors = Answer.all_objects.filter(question=instance).select_related("author")
    _later(instance.author, *(answer.author for answer in authors))


@receiver(post_save, sender=ProjectTask, dispatch_uid="reputation.task")
def _task(sender: Any, instance: ProjectTask, **kwargs: Any) -> None:
    if instance.assignee_id:
        _later(instance.assignee)


@receiver(post_save, sender=Project, dispatch_uid="reputation.project")
def _project(sender: Any, instance: Project, **kwargs: Any) -> None:
    members = ProjectMember.objects.filter(project=instance).select_related("user")
    _later(*(member.user for member in members))


@receiver([post_save, post_delete], sender=Recommendation, dispatch_uid="reputation.recommendation")
def _recommendation(sender: Any, instance: Recommendation, **kwargs: Any) -> None:
    _later(instance.recommended)
