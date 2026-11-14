"""Opérations d'administration des référentiels."""

from django.db import models, transaction

from common.exceptions import BusinessRuleViolation

from .models import Tag, Technology


def _reassign_m2m(source: models.Model, target: models.Model) -> None:
    """Reporte toutes les relations Many-to-Many de ``source`` vers ``target``."""
    for relation in source._meta.related_objects:
        if not relation.many_to_many:
            continue
        accessor = relation.get_accessor_name()
        for related in getattr(source, accessor).all():
            getattr(related, relation.field.name).add(target)
            getattr(related, relation.field.name).remove(source)


@transaction.atomic
def merge_reference_items(source: Tag | Technology, target: Tag | Technology) -> None:
    """Fusionne un doublon dans l'élément cible puis désactive le doublon.

    Les relations M2M (publications, projets) sont reportées ; les relations
    à contrainte d'unicité (compétences) sont fusionnées par le module concerné
    via ``on_merge`` lorsqu'il existe. L'historique n'est jamais supprimé.
    """
    if type(source) is not type(target):
        raise BusinessRuleViolation("Seuls deux éléments du même référentiel sont fusionnables.")
    if source.pk == target.pk:
        raise BusinessRuleViolation("Un élément ne peut pas être fusionné avec lui-même.")
    _reassign_m2m(source, target)
    hook = getattr(source, "on_merge", None)
    if callable(hook):  # pragma: no cover - extension réservée aux modèles qui la définissent
        hook(target)
    source.is_active = False
    source.save(update_fields=["is_active", "updated_at"])
