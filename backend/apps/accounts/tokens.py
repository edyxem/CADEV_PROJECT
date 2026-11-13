"""Jetons à usage unique : vérification d'e-mail, changement d'adresse, sessions JWT."""

from typing import Any

from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core import signing
from django.core.exceptions import ValidationError
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User

EMAIL_CHANGE_SALT = "accounts.email-change"


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    """Jeton invalidé dès que l'adresse est vérifiée ou modifiée."""

    key_salt = "accounts.email-verification"

    def _make_hash_value(self, user: User, timestamp: int) -> str:
        return f"{user.pk}{user.email}{user.email_verified}{timestamp}"


email_verification_token = EmailVerificationTokenGenerator()


def encode_uid(user: User) -> str:
    return urlsafe_base64_encode(force_bytes(user.pk))


def get_user_from_uid(uid: str) -> User | None:
    """Retrouve un compte actif à partir d'un identifiant encodé, sans lever d'erreur."""
    try:
        pk = force_str(urlsafe_base64_decode(uid))
        return User.objects.filter(pk=pk, is_active=True).first()
    except (TypeError, ValueError, OverflowError, UnicodeDecodeError, ValidationError):
        return None


def make_email_change_token(user: User, new_email: str) -> str:
    return signing.dumps({"uid": str(user.pk), "email": new_email}, salt=EMAIL_CHANGE_SALT)


def read_email_change_token(token: str) -> dict[str, Any] | None:
    try:
        return signing.loads(token, salt=EMAIL_CHANGE_SALT, max_age=settings.PASSWORD_RESET_TIMEOUT)
    except signing.BadSignature:
        return None


def issue_tokens(user: User) -> tuple[str, str]:
    """Crée une paire (access, refresh) pour un compte."""
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token), str(refresh)


def blacklist_refresh_token(raw_token: str | None) -> None:
    """Révoque un refresh token ; silencieux s'il est absent ou déjà invalide."""
    if not raw_token:
        return
    try:
        RefreshToken(raw_token).blacklist()
    except TokenError:
        return


def revoke_all_sessions(user: User) -> None:
    """Révoque tous les refresh tokens encore valides d'un compte."""
    BlacklistedToken.objects.bulk_create(
        [BlacklistedToken(token=token) for token in OutstandingToken.objects.filter(user=user)],
        ignore_conflicts=True,
    )
