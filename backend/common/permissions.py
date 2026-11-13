"""Permissions globales. Les rôles de projet sont gérés dans ``apps.projects``."""

from typing import Any

from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request


def is_moderator(user: Any) -> bool:
    return bool(user and user.is_authenticated and user.is_moderator)


def is_admin(user: Any) -> bool:
    return bool(user and user.is_authenticated and user.is_admin)


class IsModerator(BasePermission):
    """Réservé aux modérateurs et aux administrateurs."""

    message = "Action réservée à la modération."

    def has_permission(self, request: Request, view: Any) -> bool:
        return is_moderator(request.user)


class IsAdmin(BasePermission):
    """Réservé aux administrateurs."""

    message = "Action réservée aux administrateurs."

    def has_permission(self, request: Request, view: Any) -> bool:
        return is_admin(request.user)


class IsAdminOrReadOnly(BasePermission):
    """Lecture publique, écriture réservée aux administrateurs (référentiels)."""

    message = "Action réservée aux administrateurs."

    def has_permission(self, request: Request, view: Any) -> bool:
        return request.method in SAFE_METHODS or is_admin(request.user)


class IsOwnerOrReadOnly(BasePermission):
    """Lecture ouverte ; écriture réservée à l'auteur de l'objet.

    L'attribut portant l'auteur est ``author`` par défaut ; une vue peut le
    changer avec ``owner_field``.
    """

    message = "Vous ne pouvez modifier que vos propres contenus."

    def has_permission(self, request: Request, view: Any) -> bool:
        return request.method in SAFE_METHODS or bool(
            request.user and request.user.is_authenticated
        )

    def has_object_permission(self, request: Request, view: Any, obj: Any) -> bool:
        if request.method in SAFE_METHODS:
            return True
        owner_id = getattr(obj, f"{getattr(view, 'owner_field', 'author')}_id", None)
        return owner_id is not None and owner_id == request.user.pk
