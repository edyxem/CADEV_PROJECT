import factory

from apps.accounts.models import User

DEFAULT_PASSWORD = "Baobab-Solide-2026"


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: f"membre{n}")
    email = factory.LazyAttribute(lambda user: f"{user.username}@example.org")
    email_verified = True
    role = User.Role.MEMBER

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        self.set_password(extracted or DEFAULT_PASSWORD)
        if create:
            self.save(update_fields=["password"])
