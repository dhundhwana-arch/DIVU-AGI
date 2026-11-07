"""Identifier and time helpers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime


def new_id() -> str:
    """Return a new UUIDv4 string. Used for every primary key."""
    return str(uuid.uuid4())


def utcnow() -> datetime:
    """Timezone-aware UTC "now". All persisted timestamps are UTC."""
    return datetime.now(UTC)


def short_id(length: int = 12) -> str:
    """Short, URL-safe, non-sequential identifier (e.g. API key prefixes)."""
    return uuid.uuid4().hex[:length]


def is_uuid(value: str) -> bool:
    try:
        uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return False
    return True
