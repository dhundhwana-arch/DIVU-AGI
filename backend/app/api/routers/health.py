"""Liveness and readiness probes (unauthenticated, exempt from rate limiting)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app import __version__
from app.api.deps import get_settings_dep as settings_dependency
from app.core.config import Settings
from app.db.session import get_session
from app.schemas.system import HealthResponse, ReadyResponse
from app.services.system_service import SystemService

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live", response_model=HealthResponse, summary="Liveness probe")
async def live(settings: Annotated[Settings, Depends(settings_dependency)]) -> HealthResponse:
    """Always 200 while the process can serve requests."""
    return HealthResponse(
        status="ok", version=__version__, environment=settings.app_env, components=[]
    )


@router.get("/ready", response_model=ReadyResponse, summary="Readiness probe")
async def ready(
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(settings_dependency)],
) -> ReadyResponse:
    """200 when every hard dependency is reachable, 503 otherwise. Never fakes a result."""
    service = SystemService(session, settings)
    is_ready, components = await service.readiness()
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadyResponse(
        status="ok" if is_ready else "degraded",
        version=__version__,
        environment=settings.app_env,
        components=components,
        ready=is_ready,
    )


@router.get("/version", summary="Build information")
async def version() -> dict[str, str]:
    return {"app": "DIVU AI", "version": __version__, "founder": "DIVYESH BAMBHANIYA"}
