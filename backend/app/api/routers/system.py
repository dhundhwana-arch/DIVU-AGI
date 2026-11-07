"""Public system information and admin configuration view."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Principal, require_admin
from app.db.session import get_session
from app.schemas.system import SystemInfoResponse
from app.services.system_service import SystemService

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/info", response_model=SystemInfoResponse, summary="Public system information")
async def system_info(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SystemInfoResponse:
    """Brand, version, enabled features, configured providers and detected capabilities."""
    service = SystemService(session)
    return await service.info()


@router.get(
    "/config",
    summary="Redacted configuration (admin)",
    dependencies=[Depends(require_admin)],
)
async def system_config(
    session: Annotated[AsyncSession, Depends(get_session)],
    _principal: Annotated[Principal, Depends(require_admin)],
) -> dict[str, Any]:
    """Returns the full configuration with every secret value replaced by `***redacted***`."""
    service = SystemService(session)
    return service.config_view()


@router.get("/me", summary="Current principal")
async def current_principal_info(
    principal: Annotated[Principal, Depends(require_admin)],
) -> dict[str, Any]:
    return {
        "user_id": principal.user_id,
        "email": principal.user.email,
        "roles": principal.roles,
        "auth_method": principal.auth_method,
        "is_superuser": bool(principal.user.is_superuser),
    }
