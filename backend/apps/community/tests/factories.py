import factory
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.catalog.tests.factories import CategoryFactory
from apps.community.models import Answer, Comment, ContentStatus, Post


class PostFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Post

    author = factory.SubFactory(UserFactory)
    category = factory.SubFactory(CategoryFactory)
    type = Post.Type.DISCUSSION
    title = factory.Sequence(lambda n: f"Discussion technique numéro {n}")
    content = "<p>Contenu de démonstration suffisamment détaillé.</p>"
    status = ContentStatus.PUBLISHED
    published_at = factory.LazyFunction(timezone.now)
    last_activity_at = factory.LazyFunction(timezone.now)


class QuestionFactory(PostFactory):
    type = Post.Type.QUESTION
    title = factory.Sequence(lambda n: f"Comment résoudre le problème {n} ?")


class CommentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Comment

    post = factory.SubFactory(PostFactory)
    author = factory.SubFactory(UserFactory)
    content = "<p>Merci pour le partage.</p>"


class AnswerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Answer

    question = factory.SubFactory(QuestionFactory)
    author = factory.SubFactory(UserFactory)
    content = "<p>Essayez de vérifier la configuration.</p>"
