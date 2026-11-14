"""Règles métier des profils : compétences, liens, avatar."""

from collections.abc import Iterable
from typing import Any

from django.core.files.uploadedfile import UploadedFile
from django.db import transaction

from apps.accounts.models import User
from common.exceptions import BusinessRuleViolation
from common.images import remove_image, replace_image

from .models import DeveloperProfile, SocialLink, UserSkill

MAX_SKILLS = 30
MAX_LINKS = 10
AVATAR_SIZE = (512, 512)


def _verification_status(existing: UserSkill | None, evidence_url: str) -> str:
    """Une validation par les pairs ne se perd pas ; sinon le statut découle de la preuve.

    Ajouter un lien ne rend jamais une compétence « vérifiée » : au mieux,
    elle passe à « preuve ajoutée (non vérifiée) ».
    """
    statuses = UserSkill.VerificationStatus
    if existing and existing.verification_status == statuses.PEER_REVIEWED:
        return statuses.PEER_REVIEWED
    return statuses.EVIDENCE_ADDED if evidence_url else statuses.SELF_DECLARED


@transaction.atomic
def set_skills(user: User, items: Iterable[dict[str, Any]], *, replace: bool) -> None:
    """Crée ou met à jour les compétences ; ``replace`` supprime celles non listées."""
    items = list(items)
    technologies = [item["technology"] for item in items]
    if len({technology.pk for technology in technologies}) != len(technologies):
        raise BusinessRuleViolation("Une technologie ne peut figurer qu'une fois.")

    existing = {
        skill.technology_id: skill
        for skill in UserSkill.objects.select_for_update().filter(user=user)
    }
    final_count = len(items) if replace else len(existing.keys() | {t.pk for t in technologies})
    if final_count > MAX_SKILLS:
        raise BusinessRuleViolation(f"Maximum {MAX_SKILLS} compétences par profil.")

    for item in items:
        technology = item["technology"]
        evidence_url = item.get("evidence_url", "") or ""
        current = existing.get(technology.pk)
        UserSkill.objects.update_or_create(
            user=user,
            technology=technology,
            defaults={
                "level": item["level"],
                "years_experience": item.get("years_experience"),
                "evidence_url": evidence_url,
                "verification_status": _verification_status(current, evidence_url),
            },
        )
    if replace:
        UserSkill.objects.filter(user=user).exclude(technology__in=technologies).delete()


def add_social_link(user: User, **data: Any) -> SocialLink:
    if SocialLink.objects.filter(user=user).count() >= MAX_LINKS:
        raise BusinessRuleViolation(f"Maximum {MAX_LINKS} liens par profil.")
    if SocialLink.objects.filter(user=user, url=data["url"]).exists():
        raise BusinessRuleViolation("Ce lien figure déjà sur votre profil.")
    return SocialLink.objects.create(user=user, **data)


def update_avatar(profile: DeveloperProfile, upload: UploadedFile) -> DeveloperProfile:
    return replace_image(profile, "avatar", upload, max_size=AVATAR_SIZE)


def remove_avatar(profile: DeveloperProfile) -> None:
    remove_image(profile, "avatar")
