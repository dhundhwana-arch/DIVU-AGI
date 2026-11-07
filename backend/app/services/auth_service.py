"""Authentication: registration, login, token issuance, rotation, logout, API keys."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.errors import InvalidCredentialsError, NotFoundError, TokenInvalidError
from app.core.ids import new_id, short_id, utcnow
from app.db.models.api_key import ApiKey
from app.db.models.token import RefreshToken
from app.db.models.user import User
from app.security.passwords import (
    hash_password,
    needs_rehash,
    validate_password_strength,
    verify_password,
)
from app.security.tokens import create_token, hash_token, verify_token_hash
from app.services.audit import AuditService
from app.services.user_service import UserService

API_KEY_PREFIX = "dvk"


@dataclass
class TokenPair:
    access_token: str
    refresh_token: str
    expires_in: int
    refresh_expires_in: int


class AuthService:
    """All authentication flows. Audit events are recorded for every outcome."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        settings: Settings | None = None,
        audit: AuditService | None = None,
    ) -> None:
        self._session = session
        self._settings = settings or get_settings()
        self._audit = audit or AuditService(session)
        self._users = UserService(session)

    # ---------------- Registration ----------------
    async def register(
        self,
        *,
        email: str,
        password: str,
        full_name: str = "",
        role_names: list[str] | None = None,
        ip_address: str = "",
        user_agent: str = "",
        request_id: str = "",
    ) -> User:
        if not self._settings.allow_public_registration and not role_names:
            # Administrators create accounts through the admin API, which passes explicit roles.
            from app.core.errors import PermissionDeniedError

            raise PermissionDeniedError("Public registration is disabled on this deployment.")
        user = await self._users.create_user(
            email=email, password=password, full_name=full_name, role_names=role_names
        )
        await self._audit.record(
            "auth.register",
            actor_id=user.id,
            actor_email=user.email,
            resource_type="user",
            resource_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            message="Account created.",
            metadata={"roles": user.role_names},
        )
        return user

    # ---------------- Login ----------------
    async def authenticate(
        self,
        *,
        email: str,
        password: str,
        ip_address: str = "",
        user_agent: str = "",
        request_id: str = "",
    ) -> User:
        user = await self._users.get_by_email(email)
        if user is None:
            await self._audit.record(
                "auth.login.failure",
                actor_email=email,
                outcome="failure",
                resource_type="user",
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id,
                message="Unknown account.",
                metadata={"reason": "unknown_account"},
                commit=True,
            )
            raise InvalidCredentialsError()

        if user.is_locked:
            await self._audit.record(
                "auth.login.failure",
                actor_id=user.id,
                actor_email=user.email,
                outcome="blocked",
                resource_type="user",
                resource_id=user.id,
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id,
                message="Account temporarily locked after repeated failures.",
                metadata={"reason": "locked"},
                commit=True,
            )
            raise InvalidCredentialsError("Account is temporarily locked. Please try again later.")

        if not user.is_active or not verify_password(password, user.hashed_password):
            user.failed_login_count = int(user.failed_login_count or 0) + 1
            if user.failed_login_count >= self._settings.max_failed_logins:
                user.locked_until = utcnow() + timedelta(seconds=self._settings.lockout_seconds)
                user.failed_login_count = 0
            self._session.add(user)
            await self._audit.record(
                "auth.login.failure",
                actor_id=user.id,
                actor_email=user.email,
                outcome="failure",
                resource_type="user",
                resource_id=user.id,
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id,
                message="Invalid credentials.",
                metadata={"reason": "invalid_credentials"},
                commit=True,
            )
            raise InvalidCredentialsError()

        # Success: reset failure state, upgrade legacy hashes opportunistically.
        user.failed_login_count = 0
        user.locked_until = None
        user.last_login_at = utcnow()
        if needs_rehash(user.hashed_password, iterations=self._settings.password_hash_iterations):
            user.hashed_password = hash_password(
                password, iterations=self._settings.password_hash_iterations
            )
        self._session.add(user)
        await self._audit.record(
            "auth.login.success",
            actor_id=user.id,
            actor_email=user.email,
            resource_type="user",
            resource_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            message="Login succeeded.",
        )
        return user

    # ---------------- Tokens ----------------
    async def issue_tokens(
        self, user: User, *, user_agent: str = "", ip_address: str = ""
    ) -> TokenPair:
        access, _access_jti, access_exp = create_token(
            user.id,
            "access",
            settings=self._settings,
            extra_claims={"email": user.email, "su": bool(user.is_superuser)},
        )
        refresh, refresh_jti, refresh_exp = create_token(
            user.id, "refresh", settings=self._settings
        )
        family_id = new_id()
        record = RefreshToken(
            id=refresh_jti,
            user_id=user.id,
            token_hash=hash_token(refresh),
            family_id=family_id,
            expires_at=refresh_exp,
            created_at=utcnow(),
            user_agent=(user_agent or "")[:512],
            ip_address=(ip_address or "")[:64],
        )
        self._session.add(record)
        await self._session.flush()
        return TokenPair(
            access_token=access,
            refresh_token=refresh,
            expires_in=self._settings.access_token_ttl_seconds,
            refresh_expires_in=self._settings.refresh_token_ttl_seconds,
        )

    async def refresh(
        self,
        refresh_token: str,
        *,
        ip_address: str = "",
        user_agent: str = "",
        request_id: str = "",
    ) -> TokenPair:
        from app.security.tokens import decode_token

        payload = decode_token(refresh_token, expected_type="refresh", settings=self._settings)
        record = (
            await self._session.execute(
                select(RefreshToken).where(RefreshToken.token_hash == hash_token(refresh_token))
            )
        ).scalar_one_or_none()
        if record is None:
            raise TokenInvalidError("Unknown refresh token.")

        if record.revoked_at is not None or record.used:
            # Reuse of a rotated token: revoke the entire family (possible token theft).
            await self._revoke_family(record.family_id)
            await self._audit.record(
                "auth.token.reuse_detected",
                actor_id=record.user_id,
                outcome="blocked",
                resource_type="session",
                resource_id=record.family_id,
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id,
                message="Refresh token reuse detected; session family revoked.",
                metadata={"user_id": record.user_id},
                commit=True,
            )
            raise TokenInvalidError("This refresh token has already been used.")

        if record.expires_at <= utcnow():
            raise TokenInvalidError("This refresh token has expired.")

        user = await self._session.get(User, record.user_id)
        if user is None or not user.is_active:
            raise InvalidCredentialsError("This account is no longer active.")

        record.used = True
        record.revoked_at = utcnow()
        self._session.add(record)

        pair = await self.issue_tokens(user, user_agent=user_agent, ip_address=ip_address)
        # Keep the new token in the same family so reuse detection continues to work.
        new_record = (
            await self._session.execute(
                select(RefreshToken).where(
                    RefreshToken.token_hash == hash_token(pair.refresh_token)
                )
            )
        ).scalar_one()
        new_record.family_id = record.family_id
        record.replaced_by = new_record.id
        self._session.add(new_record)

        await self._audit.record(
            "auth.token.refresh",
            actor_id=user.id,
            actor_email=user.email,
            resource_type="session",
            resource_id=record.family_id,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            message="Token refreshed and rotated.",
        )
        _ = payload  # validated for type/expiry above
        return pair

    async def _revoke_family(self, family_id: str) -> None:
        rows = (
            (
                await self._session.execute(
                    select(RefreshToken).where(RefreshToken.family_id == family_id)
                )
            )
            .scalars()
            .all()
        )
        now = utcnow()
        for row in rows:
            row.revoked_at = now
            self._session.add(row)
        await self._session.flush()

    async def logout(
        self, refresh_token: str, *, request_id: str = "", ip_address: str = ""
    ) -> None:
        record = (
            await self._session.execute(
                select(RefreshToken).where(RefreshToken.token_hash == hash_token(refresh_token))
            )
        ).scalar_one_or_none()
        if record is None:
            return
        record.revoked_at = utcnow()
        self._session.add(record)
        await self._audit.record(
            "auth.logout",
            actor_id=record.user_id,
            resource_type="session",
            resource_id=record.id,
            ip_address=ip_address,
            request_id=request_id,
            message="Logged out.",
        )
        await self._session.flush()

    # ---------------- Password ----------------
    async def change_password(
        self,
        user: User,
        *,
        current_password: str,
        new_password: str,
        request_id: str = "",
        ip_address: str = "",
    ) -> None:
        if not verify_password(current_password, user.hashed_password):
            await self._audit.record(
                "auth.password.changed",
                actor_id=user.id,
                actor_email=user.email,
                outcome="failure",
                resource_type="user",
                resource_id=user.id,
                request_id=request_id,
                ip_address=ip_address,
                message="Password change rejected: current password incorrect.",
                metadata={"reason": "bad_current_password"},
                commit=True,
            )
            raise InvalidCredentialsError("The current password is incorrect.")
        problems = validate_password_strength(new_password)
        if problems:
            raise InvalidCredentialsError(" ".join(problems))
        user.hashed_password = hash_password(
            new_password, iterations=self._settings.password_hash_iterations
        )
        self._session.add(user)
        await self._audit.record(
            "auth.password.changed",
            actor_id=user.id,
            actor_email=user.email,
            resource_type="user",
            resource_id=user.id,
            request_id=request_id,
            ip_address=ip_address,
            message="Password changed.",
        )
        await self._session.flush()

    # ---------------- API keys ----------------
    def _generate_key(self) -> tuple[str, str, str]:
        prefix = short_id(8)
        secret = new_id().replace("-", "") + short_id(16)
        token = f"{API_KEY_PREFIX}_{prefix}_{secret}"
        return token, prefix, hash_token(token)

    async def create_api_key(
        self,
        user: User,
        *,
        name: str,
        scopes: list[str] | None = None,
        expires_in_days: int | None = None,
        request_id: str = "",
        ip_address: str = "",
    ) -> tuple[ApiKey, str]:
        token, prefix, hashed = self._generate_key()
        expires_at = utcnow() + timedelta(days=expires_in_days) if expires_in_days else None
        key = ApiKey(
            id=new_id(),
            user_id=user.id,
            name=name,
            prefix=prefix,
            hashed_key=hashed,
            scopes=list(scopes or ["chat:read", "chat:write"]),
            expires_at=expires_at,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        self._session.add(key)
        await self._audit.record(
            "api_key.created",
            actor_id=user.id,
            actor_email=user.email,
            resource_type="api_key",
            resource_id=key.id,
            request_id=request_id,
            ip_address=ip_address,
            message=f"API key '{name}' created.",
            metadata={"scopes": key.scopes},
        )
        await self._session.flush()
        return key, token

    async def list_api_keys(self, user: User) -> list[ApiKey]:
        rows = await self._session.execute(
            select(ApiKey).where(ApiKey.user_id == user.id).order_by(ApiKey.created_at.desc())
        )
        return list(rows.scalars().all())

    async def revoke_api_key(self, user: User, key_id: str, *, request_id: str = "") -> ApiKey:
        key = await self._session.get(ApiKey, key_id)
        if key is None or key.user_id != user.id:
            raise NotFoundError("API key not found.")
        key.revoked_at = utcnow()
        key.is_active = False
        self._session.add(key)
        await self._audit.record(
            "api_key.revoked",
            actor_id=user.id,
            actor_email=user.email,
            resource_type="api_key",
            resource_id=key.id,
            request_id=request_id,
            message=f"API key '{key.name}' revoked.",
        )
        await self._session.flush()
        return key

    async def verify_api_key(self, token: str) -> tuple[User, ApiKey]:
        """Resolve a personal API key to its owner. Raises on any failure."""
        try:
            _kind, prefix, _secret = token.split("_", 2)
        except ValueError as exc:
            raise InvalidCredentialsError("Malformed API key.") from exc
        row = await self._session.execute(select(ApiKey).where(ApiKey.prefix == prefix))
        candidates = row.scalars().all()
        for key in candidates:
            if verify_token_hash(token, key.hashed_key):
                if not key.is_valid:
                    raise InvalidCredentialsError("This API key has been revoked.")
                if key.expires_at and key.expires_at <= utcnow():
                    raise InvalidCredentialsError("This API key has expired.")
                user = await self._session.get(User, key.user_id)
                if user is None or not user.is_active:
                    raise InvalidCredentialsError("This API key's owner is inactive.")
                key.last_used_at = utcnow()
                self._session.add(key)
                await self._session.flush()
                return user, key
        raise InvalidCredentialsError("Invalid API key.")
