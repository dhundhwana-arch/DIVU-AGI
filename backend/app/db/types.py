"""Portable column types.

``TZDateTime`` normalises every timestamp to naive-UTC on the way into the database and returns
timezone-aware UTC datetimes on the way out, so application code behaves identically on
PostgreSQL (asyncpg) and SQLite (aiosqlite).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator


class TZDateTime(TypeDecorator):
    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def process_literal_param(self, value: Any, dialect: Dialect) -> str:  # pragma: no cover
        return str(value)
