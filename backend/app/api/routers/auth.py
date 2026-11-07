"""Authentication endpoints: register, login, token rotation, logout, profile, API keys."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Principal, get_auth_service, require_principal
from app.db.session import get_session
from app.schemas.auth import (
    ApiKeyCreatedResponse,
    ApiKeyCreateRequest,
    ApiKeyResponse,
    ChangePasswordRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.schemas.common import MessageResponse, Page
from app.security.passwords import validate_password_strength
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def _context(request: Request) -> tuple[str, str, str]:
    """(ip, user_agent, request_id) for audit records."""
    return (
        request.client.host if request.client else "",
        request.headers.get("user-agent", "")[:512],
        getattr(request.state, "request_id", ""),
    )


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an account",
)
async def register(
    payload: RegisterRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserResponse:
    ip, user_agent, request_id = _context(request)
    user = await service.register(
        email=str(payload.email),
        password=payload.password,
        full_name=payload.full_name,
        ip_address=ip,
        user_agent=user_agent,
        request_id=request_id,
    )
    _ = session  # session lifetime is managed by the dependency
    return UserResponse.from_user(user)


@router.post("/login", response_model=TokenResponse, summary="Log in and receive a token pair")
async def login(
    payload: LoginRequest,
    request: Request,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    ip, user_agent, request_id = _context(request)
    user = await service.authenticate(
        email=str(payload.email),
        password=payload.password,
        ip_address=ip,
        user_agent=user_agent,
        request_id=request_id,
    )
    pair = await service.issue_tokens(user, user_agent=user_agent, ip_address=ip)
    _ = request_id
    return TokenResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        expires_in=pair.expires_in,
        refresh_expires_in=pair.refresh_expires_in,
    )


@router.post("/refresh", response_model=TokenResponse, summary="Rotate the refresh token")
async def refresh(
    payload: RefreshRequest,
    request: Request,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    ip, user_agent, request_id = _context(request)
    pair = await service.refresh(
        payload.refresh_token, ip_address=ip, user_agent=user_agent, request_id=request_id
    )
    return TokenResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        expires_in=pair.expires_in,
        refresh_expires_in=pair.refresh_expires_in,
    )


@router.post("/logout", response_model=MessageResponse, summary="Revoke a refresh token")
async def logout(
    payload: LogoutRequest,
    request: Request,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> MessageResponse:
    ip, _user_agent, request_id = _context(request)
    await service.logout(payload.refresh_token, request_id=request_id, ip_address=ip)
    return MessageResponse(message="Logged out. The refresh token has been revoked.")


@router.get("/me", response_model=UserResponse, summary="Current user profile")
async def me(principal: Annotated[Principal, Depends(require_principal)]) -> UserResponse:
    return UserResponse.from_user(principal.user)


@router.post("/change-password", response_model=MessageResponse, summary="Change password")
async def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    principal: Annotated[Principal, Depends(require_principal)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> MessageResponse:
    ip, _user_agent, request_id = _context(request)
    await service.change_password(
        principal.user,
        current_password=payload.current_password,
        new_password=payload.new_password,
        request_id=request_id,
        ip_address=ip,
    )
    return MessageResponse(message="Your password has been changed.")


@router.post("/password/check", summary="Validate a password against the policy")
async def password_check(payload: dict[str, str]) -> dict[str, object]:
    problems = validate_password_strength(payload.get("password", ""))
    return {"valid": not problems, "problems": problems}


@router.post(
    "/api-keys",
    response_model=ApiKeyCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a personal API key (the secret is shown once)",
)
async def create_api_key(
    payload: ApiKeyCreateRequest,
    request: Request,
    principal: Annotated[Principal, Depends(require_principal)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> ApiKeyCreatedResponse:
    ip, _user_agent, request_id = _context(request)
    key, token = await service.create_api_key(
        principal.user,
        name=payload.name,
        scopes=payload.scopes,
        expires_in_days=payload.expires_in_days,
        request_id=request_id,
        ip_address=ip,
    )
    return ApiKeyCreatedResponse(
        id=key.id,
        name=key.name,
        prefix=key.prefix,
        token=token,
        scopes=list(key.scopes or []),
        created_at=_as_datetime(key.created_at),
    )


@router.get("/api-keys", summary="List your API keys")
async def list_api_keys(
    principal: Annotated[Principal, Depends(require_principal)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> Page[ApiKeyResponse]:
    keys = await service.list_api_keys(principal.user)
    items = [
        ApiKeyResponse(
            id=key.id,
            name=key.name,
            prefix=key.prefix,
            scopes=list(key.scopes or []),
            is_active=bool(key.is_active),
            created_at=_as_datetime(key.created_at),
            last_used_at=_as_datetime(key.last_used_at),
            expires_at=_as_datetime(key.expires_at),
        )
        for key in keys
    ]
    return Page[ApiKeyResponse](items=items, page=1, page_size=len(items) or 1, total=len(items))


@router.delete(
    "/api-keys/{key_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Revoke one of your API keys",
)
async def revoke_api_key(
    key_id: str,
    request: Request,
    principal: Annotated[Principal, Depends(require_principal)],
    service: Annotated[AuthService, Depends(get_auth_service)],
    response: Response,
) -> MessageResponse:
    _ip, _user_agent, request_id = _context(request)
    try:
        key = await service.revoke_api_key(principal.user, key_id, request_id=request_id)
    except Exception:
        raise
    response.status_code = status.HTTP_200_OK
    return MessageResponse(message=f"API key '{key.name}' has been revoked.")


def _as_datetime(value: object) -> datetime | None:
    return value if isinstance(value, datetime) else None
