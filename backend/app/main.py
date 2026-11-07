"""DIVU AI backend application factory.

Run with::

    uvicorn app.main:app --reload          # development
    uvicorn app.main:app --workers 4       # production (behind a reverse proxy)
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __brand__, __version__
from app.api.middleware import RateLimitMiddleware, RequestContextMiddleware
from app.api.routers import audit, auth, health, security, system, users
from app.core.config import Settings, get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.db.session import dispose_engine, get_engine, init_db

logger = get_logger(__name__)

DESCRIPTION = """
**DIVU AI** — a modular AI agent platform by **DIVYESH BAMBHANIYA** (Founder & Creator).

*Beyond Conversations. Towards Intelligence.*

This API is the backend for the DIVU AI platform. Phase 1 provides the foundation:
configuration, structured logging, the standard error envelope, the database layer,
authentication, RBAC, audit logging, rate limiting and prompt-injection screening.
"""


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    configure_logging(settings)
    logger.info(
        "startup",
        app=settings.app_name,
        version=__version__,
        environment=settings.app_env,
        database="postgres" if settings.db_is_postgres else "sqlite",
        cache=settings.cache_backend,
    )

    settings.object_storage_dir.mkdir(parents=True, exist_ok=True)

    # Development and test bootstrap: create the schema without requiring Alembic.
    # Staging/production always use `alembic upgrade head` (see DEPLOYMENT_GUIDE.md).
    if settings.app_env in {"development", "test"} and settings.db_is_sqlite:
        await init_db(get_engine())
        logger.info("database_schema_ready", mode="create_all")

    yield

    limiter = getattr(app.state, "rate_limiter", None)
    if limiter is not None:
        await limiter.close()
    await dispose_engine()
    logger.info("shutdown_complete")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the ASGI application. Exposed as a factory so tests can isolate configuration."""
    settings = settings or get_settings()
    configure_logging(settings)

    app = FastAPI(
        title=f"{__brand__} API",
        version=__version__,
        description=DESCRIPTION,
        lifespan=lifespan,
        docs_url=settings.docs_url if not settings.is_production else None,
        redoc_url=None,
        openapi_url="/openapi.json" if not settings.is_production else None,
    )
    app.state.settings = settings
    register_exception_handlers(app)

    # Middleware: the last one added is the outermost layer.
    limiter = _build_limiter(settings)
    app.state.rate_limiter = limiter
    app.add_middleware(
        RateLimitMiddleware,
        limiter=limiter,
        settings=settings,
    )
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_origin_regex=settings.cors_origin_regex or None,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-RateLimit-Limit", "X-RateLimit-Remaining"],
    )

    prefix = settings.api_v1_prefix
    app.include_router(health.router)  # unprefixed: probes live at /health/*
    app.include_router(system.router, prefix=prefix)
    app.include_router(auth.router, prefix=prefix)
    app.include_router(users.router, prefix=prefix)
    app.include_router(audit.router, prefix=prefix)
    app.include_router(security.router, prefix=prefix)

    _attach_metrics(app)
    return app


def _build_limiter(settings: Settings):
    from app.security.rate_limit import build_rate_limiter

    limiter = build_rate_limiter(settings)
    # Kept on the app so tests can inspect/reset it and lifespan can close it.
    return limiter


def _attach_metrics(app: FastAPI) -> None:
    """Optional Prometheus instrumentation (package is pinned; failure is non-fatal)."""
    try:
        from prometheus_fastapi_instrumentator import Instrumentator

        Instrumentator().instrument(app).expose(
            app, endpoint="/metrics", include_in_schema=False, should_gzip=True
        )
    except Exception as exc:  # pragma: no cover - optional dependency path
        logger.warning("metrics_disabled", reason=str(exc))


app = create_app()
