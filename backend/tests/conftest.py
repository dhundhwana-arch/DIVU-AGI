"""Shared pytest fixtures.

The suite runs with **zero external services**: every test gets a fresh SQLite database file,
an in-memory rate limiter and a local object-storage directory.
"""

from __future__ import annotations

import os
import sys
import tempfile
import uuid
from collections.abc import AsyncGenerator, Callable
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

TMP_ROOT = Path(tempfile.mkdtemp(prefix="divu-tests-"))

os.environ.update(
    {
        "DIVU_APP_ENV": "test",
        "DIVU_SECRET_KEY": "test-secret-key-with-sufficient-length-0123456789",
        "DIVU_DATABASE_URL": f"sqlite+aiosqlite:///{TMP_ROOT / 'main.db'}",
        "DIVU_CACHE_BACKEND": "memory",
        "DIVU_LOG_FORMAT": "json",
        "DIVU_LOG_LEVEL": "WARNING",
        "DIVU_OBJECT_STORAGE_PATH": str(TMP_ROOT / "objects"),
        "DIVU_PASSWORD_HASH_ITERATIONS": "1000",  # fast, still exercises the same code path
        "DIVU_RATE_LIMIT_ENABLED": "true",
        "DIVU_ALLOW_PUBLIC_REGISTRATION": "true",
        "DIVU_CORS_ORIGINS": "http://localhost:3000",
    }
)

from app.core.config import Settings, get_settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import create_engine, get_session  # noqa: E402
from app.main import create_app  # noqa: E402

TEST_PASSWORD = "Sup3rSecret!Passphrase"


@pytest.fixture(scope="session")
def settings() -> Settings:
    return get_settings()


@pytest_asyncio.fixture
async def db_engine() -> AsyncGenerator[AsyncEngine, None]:
    """A brand-new, empty database for every test."""
    path = TMP_ROOT / f"{uuid.uuid4().hex}.db"
    engine = create_engine(database_url=f"sqlite+aiosqlite:///{path}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Session for direct assertions in tests (committed on exit)."""
    factory = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
    async with factory() as session:
        yield session
        await session.commit()


@pytest_asyncio.fixture
async def app_factory(db_engine: AsyncEngine) -> Callable[..., object]:
    """Build an application whose DB dependency points at the test database."""

    factory = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)

    async def _override() -> AsyncGenerator[AsyncSession, None]:
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    def _build(overrides: Settings | None = None):
        application = create_app(overrides)
        application.dependency_overrides[get_session] = _override
        return application

    return _build


@pytest_asyncio.fixture
async def app(app_factory: Callable[..., object]):
    return app_factory()


@pytest_asyncio.fixture
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as http_client:
        yield http_client


@pytest_asyncio.fixture
async def client_factory(app_factory, db_engine) -> Callable[..., AsyncClient]:
    """Build a client bound to an app with custom settings (used for rate-limit tests)."""

    def _build(overrides: Settings | None = None) -> AsyncClient:
        application = app_factory(overrides)
        return AsyncClient(transport=ASGITransport(app=application), base_url="http://testserver")

    return _build


async def register_and_login(
    client: AsyncClient, email: str, password: str = TEST_PASSWORD
) -> dict:
    """Register a user and return ``{"user": …, "headers": …, "tokens": …}``."""
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Test User"},
    )
    assert response.status_code == 201, response.text
    user = response.json()
    tokens = await login(client, email, password)
    return {
        "user": user,
        "tokens": tokens,
        "headers": {"Authorization": f"Bearer {tokens['access_token']}"},
    }


async def login(client: AsyncClient, email: str, password: str) -> dict:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()


@pytest_asyncio.fixture
async def user_client(client: AsyncClient) -> dict:
    """An authenticated ordinary user (role: user)."""
    return await register_and_login(client, f"user-{uuid.uuid4().hex[:8]}@divu.ai")


@pytest_asyncio.fixture
async def admin_client(client: AsyncClient, db_session: AsyncSession) -> dict:
    """An authenticated administrator (role: admin) sharing the same HTTP client."""
    from app.services.user_service import UserService

    email = f"admin-{uuid.uuid4().hex[:8]}@divu.ai"
    service = UserService(db_session)
    await service.create_user(
        email=email, password=TEST_PASSWORD, full_name="Admin", role_names=["admin"]
    )
    await db_session.commit()
    tokens = await login(client, email, TEST_PASSWORD)
    return {
        "tokens": tokens,
        "headers": {"Authorization": f"Bearer {tokens['access_token']}"},
        "email": email,
    }
