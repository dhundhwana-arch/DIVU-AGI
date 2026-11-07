"""Refresh tokens (persisted as hashes, with rotation + reuse detection)."""

from __future__ import annotations

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin
from app.db.types import TZDateTime


class RefreshToken(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = {"extend_existing": True}

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    family_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    expires_at = mapped_column(TZDateTime(), nullable=False)
    created_at = mapped_column(TZDateTime(), nullable=False)
    revoked_at = mapped_column(TZDateTime(), nullable=True)
    replaced_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    user_agent: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    ip_address: Mapped[str] = mapped_column(String(64), default="", nullable=False)

    @property
    def is_valid(self) -> bool:
        return self.revoked_at is None


__all__ = ["DateTime", "RefreshToken"]
