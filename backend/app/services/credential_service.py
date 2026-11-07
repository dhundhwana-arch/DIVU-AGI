"""Encrypted third-party credential storage (BYO provider keys)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.core.ids import new_id, utcnow
from app.db.models.credential import ProviderCredential
from app.schemas.credential import CredentialCreateRequest, CredentialResponse
from app.security.encryption import decrypt_secret, encrypt_secret, mask_secret


class CredentialService:
    """Encrypts before write, masks on read. Plaintext never leaves this service."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, user_id: str, payload: CredentialCreateRequest) -> ProviderCredential:
        credential = ProviderCredential(
            id=new_id(),
            user_id=user_id,
            provider=payload.provider.strip().lower(),
            label=payload.label.strip(),
            encrypted_value=encrypt_secret(payload.value),
            masked_value=mask_secret(payload.value),
            is_active=True,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        self._session.add(credential)
        await self._session.flush()
        return credential

    async def list_for_user(self, user_id: str) -> list[ProviderCredential]:
        rows = await self._session.execute(
            select(ProviderCredential)
            .where(ProviderCredential.user_id == user_id)
            .order_by(ProviderCredential.created_at.desc())
        )
        return list(rows.scalars().all())

    async def reveal(self, user_id: str, credential_id: str) -> str:
        """Return the decrypted secret. Every reveal is an auditable event at the API layer."""
        credential = await self._session.get(ProviderCredential, credential_id)
        if credential is None or credential.user_id != user_id:
            raise NotFoundError("Credential not found.")
        return decrypt_secret(credential.encrypted_value)

    async def delete(self, user_id: str, credential_id: str) -> None:
        credential = await self._session.get(ProviderCredential, credential_id)
        if credential is None or credential.user_id != user_id:
            raise NotFoundError("Credential not found.")
        await self._session.delete(credential)
        await self._session.flush()


def to_response(credential: ProviderCredential) -> CredentialResponse:
    def _dt(value: object) -> datetime | None:
        return value if isinstance(value, datetime) else None

    return CredentialResponse(
        id=credential.id,
        provider=credential.provider,
        label=credential.label,
        masked_value=credential.masked_value,
        is_active=bool(credential.is_active),
        created_at=_dt(credential.created_at),
    )
