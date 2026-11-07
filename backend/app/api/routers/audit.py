"""Audit log access (admin)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Principal, require_admin
from app.db.session import get_session
from app.schemas.audit import AuditActionCatalog, AuditLogResponse
from app.schemas.common import Page
from app.services.audit import CATALOG, AuditService

router = APIRouter(prefix="/audit", tags=["audit"], dependencies=[Depends(require_admin)])


@router.get("", response_model=Page[AuditLogResponse], summary="Query the audit log")
async def list_audit(
    session: Annotated[AsyncSession, Depends(get_session)],
    _principal: Annotated[Principal, Depends(require_admin)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
    action: Annotated[str, Query(max_length=80)] = "",
    actor_id: Annotated[str, Query(max_length=36)] = "",
    outcome: Annotated[str, Query(max_length=32)] = "",
) -> Page[AuditLogResponse]:
    service = AuditService(session)
    result = await service.list_recent(
        page=page,
        page_size=page_size,
        action=action or None,
        actor_id=actor_id or None,
        outcome=outcome or None,
    )
    return Page[AuditLogResponse](
        items=[AuditLogResponse.model_validate(row) for row in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
    )


@router.get("/actions", response_model=AuditActionCatalog, summary="Known audit actions")
async def audit_actions() -> AuditActionCatalog:
    return AuditActionCatalog(actions=sorted(set(CATALOG)))
