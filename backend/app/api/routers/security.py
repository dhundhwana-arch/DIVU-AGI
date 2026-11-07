"""Security utilities exposed to clients: prompt-injection screening and credential vault."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Principal, require_principal
from app.db.session import get_session
from app.schemas.common import MessageResponse
from app.schemas.credential import (
    CredentialCreateRequest,
    CredentialResponse,
    CredentialRevealResponse,
)
from app.security.injection import THRESHOLDS, screen_text
from app.services.audit import AuditService
from app.services.credential_service import CredentialService, to_response

router = APIRouter(prefix="/security", tags=["security"])


@router.post("/screen", summary="Screen text for prompt-injection indicators")
async def screen(
    payload: dict[str, str],
    principal: Annotated[Principal, Depends(require_principal)],
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, object]:
    text = payload.get("text", "")
    source = payload.get("source", "user")
    if source not in THRESHOLDS:
        source = "user"
    result = screen_text(text, source=source)
    if result.blocked:
        audit = AuditService(session)
        await audit.record(
            "security.injection.blocked",
            actor_id=principal.user_id,
            actor_email=principal.user.email,
            outcome="blocked",
            resource_type="prompt_injection",
            ip_address=request.client.host if request.client else "",
            request_id=getattr(request.state, "request_id", ""),
            message="Prompt-injection screening flagged the submitted text.",
            metadata={"categories": result.categories, "score": result.risk_score},
        )
    return result.as_dict()


@router.get("/policy", summary="Screening thresholds per content source")
async def policy() -> dict[str, object]:
    return {"thresholds": THRESHOLDS}


@router.post(
    "/credentials", response_model=CredentialResponse, summary="Store an encrypted credential"
)
async def create_credential(
    payload: CredentialCreateRequest,
    principal: Annotated[Principal, Depends(require_principal)],
    session: Annotated[AsyncSession, Depends(get_session)],
    request: Request,
) -> CredentialResponse:
    service = CredentialService(session)
    credential = await service.create(principal.user_id, payload)
    audit = AuditService(session)
    await audit.record(
        "credential.created",
        actor_id=principal.user_id,
        actor_email=principal.user.email,
        resource_type="credential",
        resource_id=credential.id,
        ip_address=request.client.host if request.client else "",
        request_id=getattr(request.state, "request_id", ""),
        message=f"Encrypted credential stored for provider '{credential.provider}'.",
        metadata={"provider": credential.provider},
    )
    return to_response(credential)


@router.get("/credentials", summary="List stored credentials (masked)")
async def list_credentials(
    principal: Annotated[Principal, Depends(require_principal)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, object]:
    service = CredentialService(session)
    items = await service.list_for_user(principal.user_id)
    return {"items": [to_response(item).model_dump() for item in items]}


@router.post(
    "/credentials/{credential_id}/reveal",
    response_model=CredentialRevealResponse,
    summary="Reveal a stored credential (audited)",
)
async def reveal_credential(
    credential_id: str,
    principal: Annotated[Principal, Depends(require_principal)],
    session: Annotated[AsyncSession, Depends(get_session)],
    request: Request,
) -> CredentialRevealResponse:
    service = CredentialService(session)
    value = await service.reveal(principal.user_id, credential_id)
    audit = AuditService(session)
    await audit.record(
        "credential.revealed",
        actor_id=principal.user_id,
        actor_email=principal.user.email,
        resource_type="credential",
        resource_id=credential_id,
        ip_address=request.client.host if request.client else "",
        request_id=getattr(request.state, "request_id", ""),
        message="Credential revealed to its owner.",
    )
    return CredentialRevealResponse(id=credential_id, provider="", value=value)


@router.delete("/credentials/{credential_id}", response_model=MessageResponse)
async def delete_credential(
    credential_id: str,
    principal: Annotated[Principal, Depends(require_principal)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MessageResponse:
    service = CredentialService(session)
    await service.delete(principal.user_id, credential_id)
    return MessageResponse(message="Credential deleted.")
