"""Audit logging service.

Audit records are written for every security-relevant action: authentication attempts
(success and failure), token refresh/reuse, role changes, key management, admin operations.
Records are append-only at the application level (no update or delete path exists).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ids import new_id, utcnow
from app.db.models.audit import AuditLog
from app.schemas.common import Page

# Canonical action vocabulary (kept in one place so the UI and tests stay in sync).
ACTION_REGISTER = "auth.register"
ACTION_LOGIN_SUCCESS = "auth.login.success"
ACTION_LOGIN_FAILURE = "auth.login.failure"
ACTION_LOGOUT = "auth.logout"
ACTION_TOKEN_REFRESH = "auth.token.refresh"
ACTION_TOKEN_REUSE = "auth.token.reuse_detected"
ACTION_PASSWORD_CHANGED = "auth.password.changed"
ACTION_API_KEY_CREATED = "api_key.created"
ACTION_API_KEY_REVOKED = "api_key.revoked"
ACTION_USER_ROLE_CHANGED = "user.role.changed"
ACTION_USER_STATUS_CHANGED = "user.status.changed"
ACTION_PERMISSION_DENIED = "security.permission_denied"
ACTION_RATE_LIMITED = "security.rate_limited"
ACTION_INJECTION_BLOCKED = "security.injection.blocked"
ACTION_CONFIG_RELOADED = "system.config.reloaded"

CATALOG: list[str] = [
    value for name, value in sorted(globals().items()) if name.startswith("ACTION_")
]


class AuditService:
    """Writes audit records. Uses the request session unless one is not available."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(
        self,
        action: str,
        *,
        actor_id: str | None = None,
        actor_email: str = "",
        actor_type: str = "user",
        outcome: str = "success",
        resource_type: str = "",
        resource_id: str = "",
        ip_address: str = "",
        user_agent: str = "",
        request_id: str = "",
        message: str = "",
        metadata: dict[str, Any] | None = None,
        commit: bool = False,
    ) -> AuditLog:
        entry = AuditLog(
            id=new_id(),
            created_at=utcnow(),
            actor_id=actor_id,
            actor_email=(actor_email or "")[:320],
            actor_type=actor_type,
            action=action,
            outcome=outcome,
            resource_type=resource_type,
            resource_id=str(resource_id)[:64] if resource_id else "",
            ip_address=(ip_address or "")[:64],
            user_agent=(user_agent or "")[:512],
            request_id=(request_id or "")[:64],
            message=message,
            metadata_json=metadata or {},
        )
        self._session.add(entry)
        await self._session.flush()
        if commit:
            # Security events must survive a rollback of the surrounding unit of work.
            await self._session.commit()
        return entry

    async def list_recent(
        self,
        *,
        page: int = 1,
        page_size: int = 50,
        action: str | None = None,
        actor_id: str | None = None,
        outcome: str | None = None,
    ) -> Page[AuditLog]:
        conditions = []
        if action:
            conditions.append(AuditLog.action == action)
        if actor_id:
            conditions.append(AuditLog.actor_id == actor_id)
        if outcome:
            conditions.append(AuditLog.outcome == outcome)
        statement = select(AuditLog)
        if conditions:
            statement = statement.where(*conditions)
        total_result = await self._session.execute(
            select(AuditLog.id).where(*conditions) if conditions else select(AuditLog.id)
        )
        total = len(total_result.scalars().all())
        rows = await self._session.execute(
            statement.order_by(AuditLog.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return Page[AuditLog](
            items=list(rows.scalars().unique().all()),
            page=page,
            page_size=page_size,
            total=total,
        )
