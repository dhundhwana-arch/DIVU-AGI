"""Credential contracts. Plaintext secrets are accepted on write, never returned on read."""

from __future__ import annotations

from datetime import datetime

from app.schemas.common import ORMModel
from pydantic import Field


class CredentialCreateRequest(ORMModel):
    provider: str = Field(min_length=2, max_length=64)
    label: str = Field(default="", max_length=120)
    value: str = Field(min_length=1, max_length=4096)


class CredentialResponse(ORMModel):
    id: str
    provider: str
    label: str = ""
    masked_value: str = ""
    is_active: bool = True
    created_at: datetime | None = None


class CredentialRevealResponse(ORMModel):
    id: str
    provider: str
    value: str  # only returned on an explicit, audited reveal request
