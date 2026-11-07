"""User administration (admin role required)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Principal, require_admin
from app.core.errors import ValidationFailedError
from app.db.session import get_session
from app.schemas.auth import UserResponse
from app.schemas.common import MessageResponse, Page
from app.services.audit import ACTION_USER_ROLE_CHANGED, ACTION_USER_STATUS_CHANGED, AuditService
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(require_admin)])


class RoleAssignment(BaseModel):
    roles: list[str] = Field(default_factory=list)


class StatusUpdate(BaseModel):
    is_active: bool


@router.get("", response_model=Page[UserResponse], summary="List users")
async def list_users(
    session: Annotated[AsyncSession, Depends(get_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
    query: Annotated[str, Query(max_length=120)] = "",
) -> Page[UserResponse]:
    service = UserService(session)
    result = await service.list_users(page=page, page_size=page_size, query=query)
    return Page[UserResponse](
        items=[UserResponse.from_user(user) for user in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
    )


@router.get("/roles", summary="List available roles")
async def list_roles(session: Annotated[AsyncSession, Depends(get_session)]) -> dict[str, object]:
    service = UserService(session)
    roles = await service.list_roles()
    return {
        "items": [
            {
                "id": role.id,
                "name": role.name,
                "description": role.description,
                "is_system": bool(role.is_system),
            }
            for role in roles
        ]
    }


@router.get("/{user_id}", response_model=UserResponse, summary="Get a user")
async def get_user(
    user_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserResponse:
    service = UserService(session)
    user = await service.get_by_id(user_id)
    return UserResponse.from_user(user)


@router.post("/{user_id}/roles", response_model=UserResponse, summary="Replace a user's roles")
async def set_user_roles(
    user_id: str,
    payload: RoleAssignment,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(require_admin)],
) -> UserResponse:
    service = UserService(session)
    user = await service.get_by_id(user_id)
    if not payload.roles:
        raise ValidationFailedError("At least one role is required.")
    await service.set_roles(user, payload.roles)
    audit = AuditService(session)
    await audit.record(
        ACTION_USER_ROLE_CHANGED,
        actor_id=principal.user_id,
        actor_email=principal.user.email,
        resource_type="user",
        resource_id=user.id,
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", "")[:512],
        request_id=getattr(request.state, "request_id", ""),
        message=f"Roles set to {sorted(payload.roles)}.",
        metadata={"roles": sorted(payload.roles)},
    )
    return UserResponse.from_user(user)


@router.patch(
    "/{user_id}/status", response_model=UserResponse, summary="Activate/deactivate a user"
)
async def set_user_status(
    user_id: str,
    payload: StatusUpdate,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(require_admin)],
) -> UserResponse:
    service = UserService(session)
    user = await service.get_by_id(user_id)
    await service.set_active(user, payload.is_active)
    audit = AuditService(session)
    await audit.record(
        ACTION_USER_STATUS_CHANGED,
        actor_id=principal.user_id,
        actor_email=principal.user.email,
        resource_type="user",
        resource_id=user.id,
        ip_address=request.client.host if request.client else "",
        request_id=getattr(request.state, "request_id", ""),
        message=f"Active status set to {payload.is_active}.",
        metadata={"is_active": payload.is_active},
    )
    return UserResponse.from_user(user)


@router.delete("/{user_id}", response_model=MessageResponse, summary="Delete a user")
async def delete_user(
    user_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(require_admin)],
) -> MessageResponse:
    service = UserService(session)
    user = await service.get_by_id(user_id)
    if user.id == principal.user_id:
        raise ValidationFailedError("You cannot delete your own account through this endpoint.")
    await service.delete_user(user)
    return MessageResponse(message="User deleted.")
