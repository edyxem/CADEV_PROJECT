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
