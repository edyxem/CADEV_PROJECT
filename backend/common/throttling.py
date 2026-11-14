"""Limitation de débit par périmètre fonctionnel."""

from typing import Any

from rest_framework.throttling import ScopedRateThrottle

SAFE_METHODS = ("GET", "HEAD", "OPTIONS")


class ScopedWriteThrottle(ScopedRateThrottle):
    """Applique ``throttle_scope`` aux écritures uniquement.

    Une vue peut étendre la limite aux lectures (recherche, par exemple) en
    déclarant ``throttle_safe_methods = True``.
    """

    def allow_request(self, request: Any, view: Any) -> bool:
        if request.method in SAFE_METHODS and not getattr(view, "throttle_safe_methods", False):
            return True
        return super().allow_request(request, view)


class ActionThrottleMixin:
    """Associe un périmètre de limitation à chaque action d'un ViewSet.

    Exemple : ``action_throttle_scopes = {"create": "content_create"}``.
    """

    action_throttle_scopes: dict[str, str] = {}

    def get_throttles(self) -> list[Any]:
        self.throttle_scope = self.action_throttle_scopes.get(getattr(self, "action", ""), "")
        return super().get_throttles()  # type: ignore[misc]
