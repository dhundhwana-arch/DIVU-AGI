"""Audit log — append-only record of security-relevant actions."""

from __future__ import annotations

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin
from app.db.types import TZDateTime


class AuditLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "audit_logs"

    created_at = mapped_column(TZDateTime(), nullable=False, index=True)
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    actor_email: Mapped[str] = mapped_column(String(320), default="", nullable=False)
    actor_type: Mapped[str] = mapped_column(String(32), default="user", nullable=False)
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    outcome: Mapped[str] = mapped_column(String(32), default="success", nullable=False)
    resource_type: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    resource_id: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    ip_address: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    user_agent: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    request_id: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
