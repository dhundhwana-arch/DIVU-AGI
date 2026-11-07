"""Shared FastAPI dependencies: settings, database session, authentication, RBAC."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.errors import AuthenticationError, PermissionDeniedError
from app.db.models.user import User
from app.db.session import get_session
from app.services.audit import ACTION_PERMISSION_DENIED, AuditService
from app.services.auth_service import AuthService

bearer_scheme = HTTPBearer(auto_error=False, scheme_name="bearer")


def get_settings_dep() -> Settings:
    return get_settings()


@dataclass
class Principal:
    """The authenticated entity behind a request."""

    user: User
    auth_method: str = "jwt"  # "jwt" | "api_key"
    scopes: list[str] = field(default_factory=list)

    @property
    def user_id(self) -> str:
        return self.user.id

    @property
    def roles(self) -> list[str]:
        return self.user.role_names

    def has_role(self, name: str) -> bool:
        return self.user.is_superuser or name in self.roles

    def has_any_role(self, names: tuple[str, ...]) -> bool:
        return any(self.has_role(name) for name in names)


async def get_principal(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
) -> Principal | None:
    """Resolve the caller from a bearer JWT or a personal API key. ``None`` if absent."""
    api_key = request.headers.get("x-api-key")
    if api_key:
        service = AuthService(session)
        user, key = await service.verify_api_key(api_key)
        return Principal(user=user, auth_method="api_key", scopes=list(key.scopes or []))

    if credentials and credentials.credentials:
        from app.security.tokens import decode_token

        settings = get_settings()
        payload = decode_token(credentials.credentials, expected_type="access", settings=settings)
        user = await session.get(User, payload["sub"])
        if user is None or not user.is_active:
            raise AuthenticationError("This account is not available.")
        return Principal(user=user, auth_method="jwt", scopes=list(payload.get("scopes") or []))
    return None


async def require_principal(
    principal: Annotated[Principal | None, Depends(get_principal)],
) -> Principal:
    if principal is None:
        raise AuthenticationError("Authentication credentials were not provided.")
    return principal


def require_roles(*names: str):
    """Dependency factory enforcing role membership (superusers bypass)."""

    async def _guard(
        request: Request,
        principal: Annotated[Principal, Depends(require_principal)],
        session: Annotated[AsyncSession, Depends(get_session)],
    ) -> Principal:
        if not principal.has_any_role(names):
            audit = AuditService(session)
            await audit.record(
                ACTION_PERMISSION_DENIED,
                actor_id=principal.user_id,
                actor_email=principal.user.email,
                outcome="denied",
                resource_type="endpoint",
                resource_id=f"{request.method} {request.url.path}",
                ip_address=(request.client.host if request.client else ""),
                user_agent=request.headers.get("user-agent", ""),
                request_id=getattr(request.state, "request_id", ""),
                message=f"Required one of roles: {', '.join(names)}.",
                metadata={"required_roles": list(names)},
            )
            await session.commit()
            raise PermissionDeniedError(
                "You do not have permission to perform this action.",
                details={"required_roles": list(names)},
            )
        return principal

    return _guard


require_admin = require_roles("admin")


async def get_audit_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AuditService:
    return AuditService(session)


async def get_auth_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AuthService:
    return AuthService(session)
