"""Async engine, session factory and FastAPI dependency."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings, get_settings
from app.db.base import Base


def create_engine(
    settings: Settings | None = None, *, database_url: str | None = None
) -> AsyncEngine:
    """Build an AsyncEngine tuned for the configured backend."""
    settings = settings or get_settings()
    url = database_url or settings.database_url

    kwargs: dict[str, Any] = {"echo": settings.db_echo, "future": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        kwargs.update(
            {
                "pool_size": settings.db_pool_size,
                "max_overflow": settings.db_max_overflow,
                "pool_pre_ping": True,
            }
        )
    return create_async_engine(url, **kwargs)


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_engine()
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(), expire_on_commit=False, autoflush=False
        )
    return _session_factory


async def dispose_engine() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None


async def init_db(engine: AsyncEngine | None = None) -> None:
    """Create all tables. Production uses Alembic instead; this is for dev/test bootstrap."""
    engine = engine or get_engine()
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a transaction-scoped session."""
    session = get_session_factory()()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
