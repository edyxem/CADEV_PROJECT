"""Règles des opportunités : vérification de la source, validation, expiration."""

from typing import Any

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import exceptions

from apps.accounts.models import User
from apps.catalog.normalization import make_slug
from apps.moderation.services import audit
from apps.notifications.models import Notification
from apps.notifications.services import notify
from common.exceptions import BusinessRuleViolation
from common.permissions import is_admin, is_moderator
from common.sanitization import sanitize_rich_text, to_plain_text
from common.transitions import ensure_transition

from .models import OPPORTUNITY_TRANSITIONS, Opportunity, OpportunityInterest, Organization

Status = Opportunity.Status


def opportunity_url(opportunity: Opportunity) -> str:
    return f"/opportunites/{opportunity.pk}"


def is_verified_publisher(user: User, organization: Organization | None) -> bool:
    """Seul un membre d'une organisation vérifiée publie sans validation préalable (§L.3)."""
    return bool(
        organization
        and organization.is_verified
        and organization.members.filter(pk=user.pk).exists()
    )


# --- Organisations ------------------------------------------------------------------


@transaction.atomic
def create_organization(*, creator: User, data: dict[str, Any]) -> Organization:
    base = make_slug(data["name"])[:120] or "organisation"
    slug, suffix = base, 2
    while Organization.objects.filter(slug=slug).exists():
        slug, suffix = f"{base}-{suffix}", suffix + 1
    organization = Organization.objects.create(
        slug=slug,
        name=to_plain_text(data["name"]),
        website=data["website"],
        description=to_plain_text(data.get("description", "")),
    )
    organization.members.add(creator)
    return organization


def verify_organization(*, organization: Organization, actor: User, verified: bool) -> Organization:
    if not is_admin(actor):
        raise exceptions.PermissionDenied(
            "La vérification d'une organisation relève des administrateurs."
        )
    organization.is_verified = verified
    organization.verified_at = timezone.now() if verified else None
    organization.verified_by = actor if verified else None
    organization.save(update_fields=["is_verified", "verified_at", "verified_by", "updated_at"])
    audit(
        actor,
        "organization.verify" if verified else "organization.unverify",
        target_type="organization",
        target_id=organization.pk,
    )
    return organization


# --- Opportunités ------------------------------------------------------------------


def _clean(data: dict[str, Any]) -> dict[str, Any]:
    if "description" in data:
        data["description"] = sanitize_rich_text(data["description"])
    for field in ("title", "organization_name", "location"):
        if field in data:
            data[field] = to_plain_text(data[field])
    return data


def _ensure_member(organization: Organization | None, user: User) -> None:
    if organization is not None and not organization.members.filter(pk=user.pk).exists():
        raise exceptions.PermissionDenied("Vous ne représentez pas cette organisation.")


def _publish_or_queue(opportunity: Opportunity, user: User) -> None:
    """Publication directe pour un partenaire vérifié, sinon file de validation."""
    target = (
        Status.PUBLISHED
        if is_verified_publisher(user, opportunity.organization)
        else Status.PENDING_REVIEW
    )
    ensure_transition(OPPORTUNITY_TRANSITIONS, opportunity.status, target)
    opportunity.status = target
    if target == Status.PUBLISHED:
        opportunity.published_at = timezone.now()


@transaction.atomic
def create_opportunity(*, publisher: User, data: dict[str, Any], submit: bool) -> Opportunity:
    data = _clean(dict(data))
    technologies = data.pop("technologies", None)
    _ensure_member(data.get("organization"), publisher)
    if data.get("deadline") and data["deadline"] < timezone.localdate():
        raise exceptions.ValidationError({"deadline": ["La date limite est déjà passée."]})
    opportunity = Opportunity(publisher=publisher, **data)
    if submit:
        _publish_or_queue(opportunity, publisher)
    opportunity.save()
    if technologies:
        opportunity.technologies.set(technologies)
    return opportunity


@transaction.atomic
def update_opportunity(
    *, opportunity: Opportunity, actor: User, data: dict[str, Any]
) -> Opportunity:
    if opportunity.publisher_id != actor.pk:
        raise exceptions.PermissionDenied("Seul l'auteur de l'annonce peut la modifier.")
    if opportunity.hidden_by_moderation:
        raise BusinessRuleViolation(
            "Cette annonce a été suspendue par la modération.", code="content_removed"
        )
    data = _clean(dict(data))
    technologies = data.pop("technologies", None)
    if "organization" in data:
        _ensure_member(data["organization"], actor)
    for field, value in data.items():
        setattr(opportunity, field, value)
    # Une annonce publiée modifiée par un publieur non vérifié repasse en validation.
    if opportunity.status == Status.PUBLISHED and not is_verified_publisher(
        actor, opportunity.organization
    ):
        opportunity.status = Status.PENDING_REVIEW
    opportunity.save()
    if technologies is not None:
        opportunity.technologies.set(technologies)
    return opportunity


def submit_opportunity(*, opportunity: Opportunity, actor: User) -> Opportunity:
    if opportunity.publisher_id != actor.pk:
        raise exceptions.PermissionDenied("Seul l'auteur de l'annonce peut la soumettre.")
    _publish_or_queue(opportunity, actor)
    opportunity.save(update_fields=["status", "published_at", "updated_at"])
    return opportunity


@transaction.atomic
def review_opportunity(
    *, opportunity: Opportunity, moderator: User, approve: bool, note: str
) -> Opportunity:
    if not is_moderator(moderator):
        raise exceptions.PermissionDenied("Action réservée à la modération.")
    if opportunity.publisher_id == moderator.pk:
        raise exceptions.PermissionDenied("Vous ne pouvez pas valider votre propre annonce.")
    opportunity = Opportunity.objects.select_for_update().get(pk=opportunity.pk)
    target = Status.PUBLISHED if approve else Status.REJECTED
    ensure_transition(OPPORTUNITY_TRANSITIONS, opportunity.status, target)
    opportunity.status = target
    opportunity.review_note = to_plain_text(note)[:500]
    opportunity.reviewed_by = moderator
    if approve:
        opportunity.published_at = timezone.now()
    opportunity.save()
    audit(
        moderator,
        "opportunity.approve" if approve else "opportunity.reject",
        target_type="opportunity",
        target_id=opportunity.pk,
        reason=opportunity.review_note,
    )
    notify(
        opportunity.publisher,
        type=Notification.Type.OPPORTUNITY_UPDATE,
        title=f"Votre annonce « {opportunity.title} » a été {'publiée' if approve else 'refusée'}",
        message=opportunity.review_note,
        actor=moderator,
        target_url=opportunity_url(opportunity),
    )
    return opportunity


@transaction.atomic
def express_interest(
    *, opportunity: Opportunity, user: User, kind: str, message: str
) -> OpportunityInterest:
    if not opportunity.is_publicly_visible:
        raise exceptions.NotFound()
    if opportunity.is_expired:
        raise BusinessRuleViolation("Cette opportunité a expiré.", code="opportunity_expired")
    if opportunity.publisher_id == user.pk:
        raise BusinessRuleViolation("Vous publiez cette annonce.", code="own_opportunity")
    try:
        with transaction.atomic():
            interest = OpportunityInterest.objects.create(
                opportunity=opportunity, user=user, kind=kind, message=to_plain_text(message)
            )
    except IntegrityError as exc:
        raise BusinessRuleViolation(
            "Vous avez déjà envoyé cette demande.", code="duplicate_interest"
        ) from exc
    notify(
        opportunity.publisher,
        type=Notification.Type.OPPORTUNITY_UPDATE,
        title=f"{user.username} s'intéresse à « {opportunity.title} »",
        actor=user,
        target_url=opportunity_url(opportunity),
    )
    return interest
