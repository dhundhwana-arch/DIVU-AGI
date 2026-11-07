"""Usage events — token, cost and latency accounting for every billable operation."""

from __future__ import annotations

from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin
from app.db.types import TZDateTime


class UsageEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "usage_events"

    created_at = mapped_column(TZDateTime(), nullable=False, index=True)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    api_key_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    conversation_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    agent_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    provider: Mapped[str] = mapped_column(String(64), default="", nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(120), default="", nullable=False, index=True)
    operation: Mapped[str] = mapped_column(String(64), default="chat", nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="success", nullable=False)
    error_code: Mapped[str] = mapped_column(String(64), default="", nullable=False)
