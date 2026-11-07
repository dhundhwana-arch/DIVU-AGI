"""JWT access/refresh tokens.

Design notes:
* Every token carries ``typ`` (``access`` | ``refresh``) — a refresh token can never be used
  as an access token.
* Refresh tokens are stored as **hashes** (the raw token is returned once and never persisted).
* Rotation: each refresh issues a new ``jti``; presenting a token whose family has already been
  rotated revokes the whole family (reuse detection).
"""

from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from jose import JWTError, jwt

from app.core.config import Settings, get_settings
from app.core.errors import TokenInvalidError
from app.core.ids import new_id, utcnow

TokenType = Literal["access", "refresh"]


def hash_token(token: str) -> str:
    """Store only this value in the database (SHA-256, constant-time comparable)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_token_hash(token: str, expected: str) -> bool:
    return hmac.compare_digest(hash_token(token), expected)


def create_token(
    subject: str,
    token_type: TokenType,
    *,
    settings: Settings | None = None,
    ttl_seconds: int | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> tuple[str, str, datetime]:
    """Create a signed token. Returns ``(token, jti, expires_at)``."""
    settings = settings or get_settings()
    if ttl_seconds is None:
        ttl_seconds = (
            settings.access_token_ttl_seconds
            if token_type == "access"
            else settings.refresh_token_ttl_seconds
        )
    now = utcnow()
    expires_at = now + timedelta(seconds=int(ttl_seconds))
    jti = new_id()
    payload: dict[str, Any] = {
        "sub": subject,
        "typ": token_type,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "jti": jti,
        "iss": "divu-ai",
    }
    if extra_claims:
        payload.update(extra_claims)
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
    return token, jti, expires_at


def decode_token(
    token: str,
    *,
    expected_type: TokenType | None = None,
    settings: Settings | None = None,
    leeway_seconds: int = 5,
) -> dict[str, Any]:
    """Decode and validate a token. Raises :class:`TokenInvalidError` on any failure."""
    settings = settings or get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"verify_aud": False, "leeway": leeway_seconds},
        )
    except JWTError as exc:
        raise TokenInvalidError("The supplied token is invalid or expired.") from exc

    if expected_type and payload.get("typ") != expected_type:
        raise TokenInvalidError("The supplied token has the wrong type.")
    if not payload.get("sub"):
        raise TokenInvalidError("The supplied token has no subject.")
    return payload


def expires_at_from_timestamp(timestamp: int) -> datetime:
    return datetime.fromtimestamp(int(timestamp), tz=UTC)


def remaining_seconds(expires_at: datetime) -> int:
    return max(0, int((expires_at - utcnow()).total_seconds()))
