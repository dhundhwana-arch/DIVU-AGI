"""Declarative base, mixins and naming conventions.

Naming conventions matter: they make Alembic autogenerate produce stable, reversible
constraint names instead of SQLite/Postgres-specific defaults.
"""

from __future__ import annotations

from sqlalchemy import DateTime, MetaData
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.ids import new_id, utcnow
from app.db.types import TZDateTime

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base class for every ORM model."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class UUIDPrimaryKeyMixin:
    """String UUIDv4 primary key (portable across Postgres and SQLite)."""

    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)


class TimestampMixin:
    created_at: Mapped[object] = mapped_column(TZDateTime(), default=utcnow, nullable=False)
    updated_at: Mapped[object] = mapped_column(
        TZDateTime(), default=utcnow, onupdate=utcnow, nullable=False
    )


# Re-exported for convenience in models.
__all__ = ["Base", "DateTime", "TZDateTime", "TimestampMixin", "UUIDPrimaryKeyMixin"]
