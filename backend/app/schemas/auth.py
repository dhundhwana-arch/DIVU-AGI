"""Authentication contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.schemas.common import ORMModel
from pydantic import EmailStr, Field, field_validator


class RegisterRequest(ORMModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)
    full_name: str = Field(default="", max_length=255)


class LoginRequest(ORMModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class RefreshRequest(ORMModel):
    refresh_token: str = Field(min_length=10)


class LogoutRequest(ORMModel):
    refresh_token: str = Field(min_length=10)


class ChangePasswordRequest(ORMModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=1, max_length=256)


class TokenResponse(ORMModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_expires_in: int


class UserResponse(ORMModel):
    id: str
    email: EmailStr
    full_name: str = ""
    is_active: bool = True
    is_superuser: bool = False
    roles: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    last_login_at: datetime | None = None

    @classmethod
    def from_user(cls, user: Any) -> UserResponse:
        """Build a response from a :class:`~app.db.models.user.User` (roles are a property)."""
        return cls(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=bool(user.is_active),
            is_superuser=bool(user.is_superuser),
            roles=user.role_names,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
        )


class ApiKeyCreateRequest(ORMModel):
    name: str = Field(min_length=1, max_length=120)
    scopes: list[str] = Field(default_factory=list)
    expires_in_days: int | None = Field(default=None, ge=1, le=365)


class ApiKeyCreatedResponse(ORMModel):
    id: str
    name: str
    prefix: str
    token: str  # returned exactly once, never recoverable afterwards
    scopes: list[str] = Field(default_factory=list)
    created_at: datetime | None = None


class ApiKeyResponse(ORMModel):
    id: str
    name: str
    prefix: str
    scopes: list[str] = Field(default_factory=list)
    is_active: bool = True
    created_at: datetime | None = None
    last_used_at: datetime | None = None
    expires_at: datetime | None = None


class PasswordStrengthResponse(ORMModel):
    valid: bool
    problems: list[str] = Field(default_factory=list)

    @field_validator("problems")
    @classmethod
    def _strip(cls, value: list[str]) -> list[str]:
        return [item for item in value if item]
