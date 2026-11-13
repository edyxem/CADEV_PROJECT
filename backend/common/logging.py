"""Formatage JSON des journaux, sans donnée sensible."""

import json
import logging
from datetime import UTC, datetime

SENSITIVE_KEYS = {"password", "token", "access", "refresh", "secret", "authorization", "cookie"}


class JSONFormatter(logging.Formatter):
    """Sérialise chaque enregistrement en une ligne JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        extra = getattr(record, "context", None)
        if isinstance(extra, dict):
            payload["context"] = {
                key: "[masqué]" if key.lower() in SENSITIVE_KEYS else value
                for key, value in extra.items()
            }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)
