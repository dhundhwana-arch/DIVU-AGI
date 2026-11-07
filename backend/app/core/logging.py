"""Structured logging with secret redaction.

Two guarantees this module must uphold (acceptance test A9):

1. Values of sensitive keys (``password``, ``token``, ``authorization`` …) are never logged.
2. Any configured secret *value* (JWT key, provider keys …) is scrubbed from every string.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import MutableMapping
from typing import Any

import structlog

from app.core.config import Settings, get_settings

SENSITIVE_KEY_HINTS = (
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "set-cookie",
    "credential",
    "private_key",
    "access_key",
    "refresh",
    "otp",
)

REDACTED = "***redacted***"


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(hint in lowered for hint in SENSITIVE_KEY_HINTS)


def redact_value(value: Any, secrets: tuple[str, ...] = ()) -> Any:
    """Recursively redact sensitive fields and known secret values."""
    if isinstance(value, Mapping):  # type: ignore[arg-type]
        return {
            key: (REDACTED if _is_sensitive_key(str(key)) else redact_value(item, secrets))
            for key, item in value.items()
        }
    if isinstance(value, list | tuple):
        return [redact_value(item, secrets) for item in value]
    if isinstance(value, str):
        result = value
        for secret in secrets:
            if secret and secret in result:
                result = result.replace(secret, REDACTED)
        return result
    return value


class RedactingProcessor:
    """structlog processor: drop/redact sensitive keys, then scrub known secret values."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings

    def _secrets(self) -> tuple[str, ...]:
        try:
            settings = self._settings or get_settings()
            return tuple(settings.secret_values())
        except Exception:  # pragma: no cover - settings unavailable during bootstrap
            return ()

    def __call__(
        self,
        _logger: Any,
        _method_name: str,
        event_dict: MutableMapping[str, Any],
    ) -> MutableMapping[str, Any]:
        secrets = self._secrets()
        cleaned: dict[str, Any] = {}
        for key, value in event_dict.items():
            if _is_sensitive_key(key):
                cleaned[key] = REDACTED
            else:
                cleaned[key] = redact_value(value, secrets)
        return cleaned


def configure_logging(settings: Settings | None = None) -> None:
    """Configure stdlib + structlog. Idempotent; safe to call at import or startup."""
    settings = settings or get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            RedactingProcessor(settings),
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.EventRenamer(to="message"),
            (
                structlog.processors.JSONRenderer()
                if settings.log_format == "json"
                else structlog.dev.ConsoleRenderer(colors=False)
            ),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        # Route through stdlib logging so handlers, levels and redaction stay consistent.
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=False,
    )

    root = logging.getLogger()
    root.setLevel(level)
    for handler in list(root.handlers):
        root.removeHandler(handler)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter("%(message)s"))
    root.addHandler(handler)
    logging.getLogger("uvicorn.access").handlers = [handler]
    logging.getLogger("uvicorn.access").propagate = False


def get_logger(name: str) -> Any:
    """Return a structlog logger bound to ``name``."""
    return structlog.get_logger(name)


# Convenience re-export for callers that need the mapping type check above.
from collections.abc import Mapping  # noqa: E402
