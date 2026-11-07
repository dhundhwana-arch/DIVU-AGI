"""Password hashing (PBKDF2-HMAC-SHA256).

Why PBKDF2 instead of bcrypt/argon2: it is in the standard library, has no C build step (so the
platform stays portable and installs stay reproducible), and OWASP's current guidance
(600,000 iterations for SHA-256) is satisfied by the default. The encoded format is
self-describing, so parameters can be raised later without breaking existing hashes.

Format: ``pbkdf2_sha256$<iterations>$<salt_b64>$<hash_b64>``
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

from app.core.config import get_settings

_ALGORITHM = "pbkdf2_sha256"
_SALT_BYTES = 16
_KEY_LENGTH = 32


def hash_password(password: str, *, iterations: int | None = None) -> str:
    """Hash a plaintext password with a fresh random salt."""
    if password is None:
        raise ValueError("password must not be None")
    rounds = iterations or get_settings().password_hash_iterations
    salt = secrets.token_bytes(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, rounds, _KEY_LENGTH)
    return "$".join(
        [
            _ALGORITHM,
            str(rounds),
            base64.b64encode(salt).decode("ascii"),
            base64.b64encode(digest).decode("ascii"),
        ]
    )


def verify_password(password: str, encoded: str | None) -> bool:
    """Constant-time verification. Returns False for malformed encodings."""
    if not encoded or password is None:
        return False
    try:
        algorithm, rounds_text, salt_b64, digest_b64 = encoded.split("$")
        if algorithm != _ALGORITHM:
            return False
        rounds = int(rounds_text)
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
    except (ValueError, TypeError):
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, rounds, len(expected))
    return hmac.compare_digest(candidate, expected)


def needs_rehash(encoded: str | None, *, iterations: int | None = None) -> bool:
    """True if the hash uses outdated parameters and should be upgraded on next login."""
    if not encoded:
        return True
    target = iterations or get_settings().password_hash_iterations
    try:
        algorithm, rounds_text, _salt, _digest = encoded.split("$")
        return algorithm != _ALGORITHM or int(rounds_text) < target
    except (ValueError, TypeError):
        return True


def validate_password_strength(password: str) -> list[str]:
    """Return a list of human-readable problems; empty list means acceptable."""
    problems: list[str] = []
    minimum = get_settings().password_min_length
    if len(password) < minimum:
        problems.append(f"Password must be at least {minimum} characters long.")
    if password.strip() == "":
        problems.append("Password must not be blank.")
    if password.lower() in {"password", "divuai", "1234567890", "qwertyuiop"}:
        problems.append("Password is too common.")
    if len(set(password)) < 5:
        problems.append("Password must contain at least 5 distinct characters.")
    return problems
