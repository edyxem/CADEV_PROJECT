"""Règles métier du compte : inscription, connexion, mots de passe, e-mail."""

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q
from rest_framework import exceptions
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from rest_framework_simplejwt.tokens import RefreshToken

from . import tokens
from .models import User, normalize_email

INVALID_LINK = "Ce lien est invalide ou a expiré."


def _frontend_link(path: str, **params: str) -> str:
    query = "&".join(f"{key}={value}" for key, value in params.items())
    return f"{settings.FRONTEND_URL.rstrip('/')}/{path}?{query}"


def _send(user_email: str, subject: str, body: str) -> None:
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [user_email], fail_silently=True)


def check_password_policy(password: str, user: User | None = None) -> None:
    """Applique la politique de robustesse Django et renvoie une erreur d'API."""
    try:
        validate_password(password, user)
    except DjangoValidationError as exc:
        raise exceptions.ValidationError({"password": list(exc.messages)}) from exc


@transaction.atomic
def register_user(*, username: str, email: str, password: str, **extra: str) -> User:
    """Crée un compte membre ; le rôle et les drapeaux ne viennent jamais du client."""
    user = User(username=username, email=normalize_email(email), **extra)
    check_password_policy(password, user)
    user.set_password(password)
    user.save()
    transaction.on_commit(lambda: send_verification_email(user))
    return user


def authenticate_user(*, identifier: str, password: str) -> User:
    """Authentifie par e-mail ou nom d'utilisateur, sans révéler lequel est faux."""
    identifier = identifier.strip()
    account = User.objects.filter(
        Q(email__iexact=identifier) | Q(username__iexact=identifier)
    ).first()
    user = authenticate(username=account.username, password=password) if account else None
    if user is None:
        raise exceptions.AuthenticationFailed(
            "Identifiants invalides ou compte désactivé.", code="invalid_credentials"
        )
    return user


def rotate_refresh_token(raw_token: str | None) -> tuple[str, str]:
    """Échange un refresh token contre une nouvelle paire et révoque l'ancien."""
    if not raw_token:
        raise exceptions.NotAuthenticated(
            "Session absente : reconnectez-vous.", code="refresh_token_missing"
        )
    try:
        refresh = RefreshToken(raw_token)
    except TokenError as exc:
        raise exceptions.AuthenticationFailed(
            "Session expirée : reconnectez-vous.", code="refresh_token_invalid"
        ) from exc

    user = User.objects.filter(pk=refresh[jwt_settings.USER_ID_CLAIM], is_active=True).first()
    refresh.blacklist()
    if user is None:
        raise exceptions.AuthenticationFailed("Compte désactivé.", code="account_disabled")
    return tokens.issue_tokens(user)


def send_verification_email(user: User) -> None:
    if user.email_verified:
        return
    link = _frontend_link(
        "verifier-email",
        uid=tokens.encode_uid(user),
        token=tokens.email_verification_token.make_token(user),
    )
    _send(
        user.email,
        "Confirmez votre adresse e-mail",
        f"Bonjour {user.username},\n\nConfirmez votre adresse en ouvrant ce lien :\n{link}\n",
    )


def verify_email(*, uid: str, token: str) -> User:
    user = tokens.get_user_from_uid(uid)
    if user is None or not tokens.email_verification_token.check_token(user, token):
        raise exceptions.ValidationError({"token": [INVALID_LINK]})
    user.email_verified = True
    user.save(update_fields=["email_verified"])
    return user


def request_password_reset(*, email: str) -> None:
    """Envoie un lien si le compte existe ; la réponse de l'API reste identique sinon."""
    user = User.objects.filter(email=normalize_email(email), is_active=True).first()
    if user is None or not user.has_usable_password():
        return
    link = _frontend_link(
        "reinitialiser-mot-de-passe",
        uid=tokens.encode_uid(user),
        token=default_token_generator.make_token(user),
    )
    _send(
        user.email,
        "Réinitialisation de votre mot de passe",
        f"Bonjour {user.username},\n\nChoisissez un nouveau mot de passe ici :\n{link}\n\n"
        "Si vous n'êtes pas à l'origine de cette demande, ignorez ce message.\n",
    )


@transaction.atomic
def confirm_password_reset(*, uid: str, token: str, new_password: str) -> User:
    user = tokens.get_user_from_uid(uid)
    if user is None or not default_token_generator.check_token(user, token):
        raise exceptions.ValidationError({"token": [INVALID_LINK]})
    check_password_policy(new_password, user)
    user.set_password(new_password)
    user.save(update_fields=["password"])
    tokens.revoke_all_sessions(user)
    return user


@transaction.atomic
def change_password(*, user: User, current_password: str, new_password: str) -> None:
    if not user.check_password(current_password):
        raise exceptions.ValidationError({"current_password": ["Mot de passe actuel incorrect."]})
    check_password_policy(new_password, user)
    user.set_password(new_password)
    user.save(update_fields=["password"])
    tokens.revoke_all_sessions(user)


def request_email_change(*, user: User, new_email: str, password: str) -> None:
    """Envoie un lien de confirmation à la nouvelle adresse, sans rien modifier."""
    new_email = normalize_email(new_email)
    if not user.check_password(password):
        raise exceptions.ValidationError({"password": ["Mot de passe incorrect."]})
    if User.objects.filter(email=new_email).exists():
        raise exceptions.ValidationError({"new_email": ["Cette adresse est déjà utilisée."]})
    link = _frontend_link("confirmer-email", token=tokens.make_email_change_token(user, new_email))
    _send(
        new_email,
        "Confirmez votre nouvelle adresse e-mail",
        f"Bonjour {user.username},\n\nValidez votre nouvelle adresse ici :\n{link}\n",
    )


@transaction.atomic
def confirm_email_change(*, token: str) -> User:
    payload = tokens.read_email_change_token(token)
    user = User.objects.filter(pk=payload["uid"], is_active=True).first() if payload else None
    if user is None:
        raise exceptions.ValidationError({"token": [INVALID_LINK]})
    if User.objects.filter(email=payload["email"]).exclude(pk=user.pk).exists():
        raise exceptions.ValidationError({"token": ["Cette adresse est déjà utilisée."]})
    user.email = payload["email"]
    user.email_verified = True
    user.save(update_fields=["email", "email_verified"])
    return user


@transaction.atomic
def deactivate_account(*, user: User, password: str) -> None:
    """Désactive le compte à la demande de son titulaire et ferme ses sessions."""
    if not user.check_password(password):
        raise exceptions.ValidationError({"password": ["Mot de passe incorrect."]})
    user.is_active = False
    user.save(update_fields=["is_active"])
    tokens.revoke_all_sessions(user)
