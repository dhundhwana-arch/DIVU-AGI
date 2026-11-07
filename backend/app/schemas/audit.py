"""Audit log contracts (admin)."""

from __future__ import annotations

from datetime import datetime

from app.schemas.common import ORMModel


class AuditLogResponse(ORMModel):
    id: str
    created_at: datetime | None = None
    actor_id: str | None = None
    actor_email: str = ""
    actor_type: str = "user"
    action: str
    outcome: str = "success"
    resource_type: str = ""
    resource_id: str = ""
    ip_address: str = ""
    request_id: str = ""
    message: str = ""
    metadata_json: dict = {}


class AuditActionCatalog(ORMModel):
    actions: list[str]
