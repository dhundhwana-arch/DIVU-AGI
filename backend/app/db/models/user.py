"""Identity: users and roles."""

from __future__ import annotations

from sqlalchemy import Boolean, Column, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.ids import utcnow
from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import TZDateTime

user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", String(36), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)


class Role(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(512), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC", nullable=False)
    locale: Mapped[str] = mapped_column(String(16), default="en", nullable=False)
    last_login_at = mapped_column(TZDateTime(), nullable=True)
    failed_login_count: Mapped[int] = mapped_column(default=0, nullable=False)
    locked_until = mapped_column(TZDateTime(), nullable=True)

    roles: Mapped[list[Role]] = relationship(secondary=user_roles, lazy="selectin", backref="users")

    @property
    def role_names(self) -> list[str]:
        return sorted(role.name for role in self.roles)

    @property
    def is_locked(self) -> bool:
        if self.locked_until is None:
            return False
        return self.locked_until > utcnow()

    def has_role(self, name: str) -> bool:
        return self.is_superuser or name in self.role_names
