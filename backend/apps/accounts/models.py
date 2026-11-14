"""Modèle utilisateur personnalisé et rôles globaux."""

import uuid
from typing import Any

from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

from .validators import USERNAME_HELP, username_format_validator, validate_username_not_reserved


def normalize_email(email: str) -> str:
    """Normalise une adresse : sans espaces, entièrement en minuscules."""
    return (email or "").strip().lower()


class UserManager(DjangoUserManager):
    """Création de comptes avec e-mail normalisé."""

    def _create_user(self, username: str, email: str | None, password: str | None, **extra: Any):
        return super()._create_user(username, normalize_email(email or ""), password, **extra)

    def create_superuser(
        self,
        username: str,
        email: str | None = None,
        password: str | None = None,
        **extra: Any,
    ):
        extra["role"] = User.Role.ADMIN
        return super().create_superuser(username, email, password, **extra)


class User(AbstractUser):
    """Compte de la plateforme. Le rôle global est la seule source des privilèges."""

    class Role(models.TextChoices):
        MEMBER = "MEMBER", "Membre"
        MODERATOR = "MODERATOR", "Modérateur"
        ADMIN = "ADMIN", "Administrateur"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(
        "nom d'utilisateur",
        max_length=30,
        unique=True,
        help_text=USERNAME_HELP,
        validators=[username_format_validator, validate_username_not_reserved],
        error_messages={"unique": "Ce nom d'utilisateur est déjà utilisé."},
    )
    email = models.EmailField(
        "adresse e-mail",
        unique=True,
        error_messages={"unique": "Un compte existe déjà avec cette adresse e-mail."},
    )
    role = models.CharField(
        "rôle global", max_length=16, choices=Role.choices, default=Role.MEMBER, db_index=True
    )
    email_verified = models.BooleanField("e-mail vérifié", default=False)
    suspended_until = models.DateTimeField(
        "suspendu jusqu'au", null=True, blank=True, help_text="Suspension temporaire (modération)."
    )
    banned_at = models.DateTimeField("banni le", null=True, blank=True)

    objects = UserManager()

    REQUIRED_FIELDS = ["email"]

    class Meta:
        verbose_name = "utilisateur"
        verbose_name_plural = "utilisateurs"
        ordering = ["-date_joined"]
        constraints = [
            models.UniqueConstraint(Lower("username"), name="accounts_user_username_ci_uniq"),
            models.UniqueConstraint(Lower("email"), name="accounts_user_email_ci_uniq"),
        ]

    def __str__(self) -> str:
        return self.username

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.email = normalize_email(self.email)
        # Les drapeaux Django découlent du rôle : ils ne se règlent jamais séparément.
        self.is_superuser = self.role == self.Role.ADMIN
        self.is_staff = self.role in {self.Role.ADMIN, self.Role.MODERATOR}
        super().save(*args, **kwargs)

    @property
    def is_suspended(self) -> bool:
        return self.suspended_until is not None and self.suspended_until > timezone.now()

    @property
    def is_banned(self) -> bool:
        return self.banned_at is not None

    @property
    def is_admin(self) -> bool:
        return self.role == self.Role.ADMIN

    @property
    def is_moderator(self) -> bool:
        """Vrai pour les modérateurs et, a fortiori, les administrateurs."""
        return self.role in {self.Role.ADMIN, self.Role.MODERATOR}
