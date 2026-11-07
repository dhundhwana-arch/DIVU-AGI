"""Symmetric encryption for secrets at rest (Fernet, AES-128-CBC + HMAC).

Used for provider credentials and any other value that must not be readable from a database
dump. The key is either an explicit Fernet key (``DIVU_ENCRYPTION_KEY``) or, in development
and test only, deterministically derived from ``DIVU_SECRET_KEY`` so a fresh clone works
without setup. Production refuses to derive (see ``Settings._validate_security_requirements``).
"""

from __future__ import annotations

import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import Settings, get_settings
from app.core.errors import AppError

_PREFIX = "enc:v1:"


class DecryptionError(AppError):
    status_code = 500
    code = "decryption_failed"
    message = "A stored secret could not be decrypted."


def derive_fernet_key(seed: str) -> bytes:
    """Derive a stable Fernet key from an arbitrary passphrase."""
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


class SecretCipher:
    """Encrypts/decrypts short secret strings."""

    def __init__(self, key: bytes) -> None:
        self._fernet = Fernet(key)

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> SecretCipher:
        settings = settings or get_settings()
        raw = settings.encryption_key
        if raw:
            key = raw.encode("utf-8") if _looks_like_fernet_key(raw) else derive_fernet_key(raw)
        else:
            key = derive_fernet_key(f"divu-dev::{settings.secret_key}")
        return cls(key)

    def encrypt(self, plaintext: str) -> str:
        return _PREFIX + self._fernet.encrypt(plaintext.encode("utf-8")).decode("ascii")

    def decrypt(self, token: str) -> str:
        if token.startswith(_PREFIX):
            token = token[len(_PREFIX) :]
        try:
            return self._fernet.decrypt(token.encode("ascii")).decode("utf-8")
        except (InvalidToken, ValueError, UnicodeDecodeError) as exc:  # pragma: no cover
            raise DecryptionError() from exc


def _looks_like_fernet_key(value: str) -> bool:
    try:
        decoded = base64.urlsafe_b64decode(value.encode("utf-8"))
    except (ValueError, TypeError):
        return False
    return len(decoded) == 32 and value.endswith("=")


@lru_cache(maxsize=1)
def get_cipher() -> SecretCipher:
    """Cached cipher instance."""
    return SecretCipher.from_settings()


def encrypt_secret(plaintext: str) -> str:
    return get_cipher().encrypt(plaintext)


def decrypt_secret(token: str) -> str:
    return get_cipher().decrypt(token)


def mask_secret(secret: str, visible: int = 4) -> str:
    """Return a display-safe mask such as ``sk-…a1b2``."""
    if not secret:
        return ""
    tail = secret[-visible:] if len(secret) > visible else ""
    return f"***{tail}"
