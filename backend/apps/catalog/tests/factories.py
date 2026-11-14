import factory

from apps.catalog.models import Category, Country, Tag, Technology


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category
        django_get_or_create = ["slug"]

    name = factory.Sequence(lambda n: f"Catégorie {n}")
    slug = factory.Sequence(lambda n: f"categorie-{n}")


class TagFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Tag
        django_get_or_create = ["slug"]

    name = factory.Sequence(lambda n: f"tag {n}")
    slug = factory.Sequence(lambda n: f"tag-{n}")


class TechnologyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Technology
        django_get_or_create = ["slug"]

    name = factory.Sequence(lambda n: f"Techno {n}")
    slug = factory.Sequence(lambda n: f"techno-{n}")


class CountryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Country
        django_get_or_create = ["code"]

    code = "SN"
    name = "Sénégal"
