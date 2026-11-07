"""Security primitives: password hashing, encryption, JWT, log redaction, rate limiting (A6, A9)."""

from __future__ import annotations

import io
import logging

import pytest
from app.core.config import Settings, get_settings
from app.core.errors import TokenInvalidError
from app.core.logging import REDACTED, configure_logging, get_logger
from app.security.encryption import decrypt_secret, encrypt_secret, mask_secret
from app.security.passwords import (
    hash_password,
    needs_rehash,
    validate_password_strength,
    verify_password,
)
from app.security.rate_limit import InMemoryRateLimiter
from app.security.tokens import create_token, decode_token
from httpx import AsyncClient


def test_password_hash_roundtrip_and_uniqueness() -> None:
    first = hash_password("Correct!Horse1", iterations=1000)
    second = hash_password("Correct!Horse1", iterations=1000)
    assert first != second  # per-password salt
    assert verify_password("Correct!Horse1", first) is True
    assert verify_password("Wrong!Horse1", first) is False
    assert verify_password("Correct!Horse1", "garbage") is False
    assert verify_password("Correct!Horse1", "") is False
    assert verify_password("Correct!Horse1", None) is False  # type: ignore[arg-type]


def test_needs_rehash_detects_outdated_parameters() -> None:
    weak = hash_password("Correct!Horse1", iterations=1000)
    assert needs_rehash(weak, iterations=600_000) is True
    assert needs_rehash(weak, iterations=1000) is False
    assert needs_rehash(None) is True
    assert needs_rehash("broken$format") is True


def test_password_policy() -> None:
    assert validate_password_strength("Sup3rSecret!Passphrase") == []
    problems = validate_password_strength("abc")
    assert any("at least" in problem for problem in problems)
    assert validate_password_strength("aaaaaaaaaaaa")  # not enough distinct characters


def test_encryption_roundtrip_and_ciphertext_is_not_plaintext() -> None:
    secret = "sk-live-abcdefgh123456"
    token = encrypt_secret(secret)
    assert token.startswith("enc:v1:")
    assert secret not in token
    assert decrypt_secret(token) == secret
    assert encrypt_secret(secret) != encrypt_secret(secret)  # randomised
    assert mask_secret(secret).endswith("3456")
    assert "abcdefgh" not in mask_secret(secret)


def test_jwt_types_are_not_interchangeable() -> None:
    settings = get_settings()
    access, _jti, _exp = create_token("user-1", "access", settings=settings)
    refresh, _rjti, _rexp = create_token("user-1", "refresh", settings=settings)

    assert decode_token(access, expected_type="access", settings=settings)["sub"] == "user-1"
    with pytest.raises(TokenInvalidError):
        decode_token(refresh, expected_type="access", settings=settings)
    with pytest.raises(TokenInvalidError):
        decode_token("tampered.token.value", expected_type="access", settings=settings)

    wrong_key = Settings(
        app_env="test", secret_key="z" * 48, database_url="sqlite+aiosqlite:///:memory:"
    )
    with pytest.raises(TokenInvalidError):
        decode_token(access, expected_type="access", settings=wrong_key)


def test_logs_never_contain_secrets_or_sensitive_fields() -> None:
    settings = Settings(
        app_env="test",
        secret_key="super-secret-signing-key-for-redaction-test-0001",
        log_level="INFO",
        log_format="json",
        database_url="sqlite+aiosqlite:///:memory:",
    )
    configure_logging(settings)
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    root = logging.getLogger()
    root.addHandler(handler)
    try:
        get_logger("test.redaction").info(
            "user signup",
            password="hunter2",
            authorization="Bearer abc.def.ghi",
            message=f"secret key is {settings.secret_key}",
            nested={"api_key": settings.secret_key},
        )
        handler.flush()
    finally:
        root.removeHandler(handler)

    output = stream.getvalue()
    assert "hunter2" not in output
    assert "Bearer abc.def.ghi" not in output
    assert settings.secret_key not in output
    assert REDACTED in output


async def test_in_memory_rate_limiter_windows() -> None:
    limiter = InMemoryRateLimiter()
    for _ in range(3):
        result = await limiter.check("client:path", limit=3, window_seconds=60)
        assert result.allowed is True
    blocked = await limiter.check("client:path", limit=3, window_seconds=60)
    assert blocked.allowed is False
    assert blocked.retry_after >= 1

    other = await limiter.check("other:path", limit=3, window_seconds=60)
    assert other.allowed is True

    await limiter.reset("client:path")
    assert (await limiter.check("client:path", limit=3, window_seconds=60)).allowed is True
    await limiter.close()


async def test_rate_limit_middleware_returns_429(client_factory) -> None:
    settings = Settings(
        app_env="test",
        secret_key="r" * 48,
        rate_limit_requests=3,
        rate_limit_window_seconds=60,
        database_url="sqlite+aiosqlite:///:memory:",
    )
    async with client_factory(settings) as http_client:
        for index in range(3):
            response = await http_client.get("/api/v1/system/info")
            assert response.status_code == 200, (index, response.text)
        limited = await http_client.get("/api/v1/system/info")
        assert limited.status_code == 429
        assert limited.json()["error"]["code"] == "rate_limited"
        assert limited.headers["Retry-After"].isdigit()


async def test_health_endpoints_are_exempt_from_rate_limiting(client_factory) -> None:
    settings = Settings(
        app_env="test",
        secret_key="r" * 48,
        rate_limit_requests=1,
        rate_limit_window_seconds=60,
        database_url="sqlite+aiosqlite:///:memory:",
    )
    async with client_factory(settings) as http_client:
        for _ in range(5):
            response = await http_client.get("/health/live")
            assert response.status_code == 200


async def test_production_requires_strong_configuration() -> None:
    with pytest.raises(ValueError):
        Settings(app_env="production", database_url="postgresql+asyncpg://u:p@localhost/db")

    valid = Settings(
        app_env="production",
        secret_key="s" * 48,
        encryption_key="k" * 44,
        database_url="postgresql+asyncpg://u:p@localhost/db",
        allow_public_registration=False,
        debug=False,
        docs_url="",
    )
    assert valid.is_production is True


async def test_rate_limiter_can_be_disabled(client_factory) -> None:
    settings = Settings(
        app_env="test",
        secret_key="r" * 48,
        rate_limit_enabled=False,
        rate_limit_requests=1,
        database_url="sqlite+aiosqlite:///:memory:",
    )
    async with client_factory(settings) as http_client:
        for _ in range(5):
            assert (await http_client.get("/api/v1/system/info")).status_code == 200


async def test_client_can_be_used_after_limit_window(client: AsyncClient) -> None:
    """Sanity check: ordinary traffic is not limited by the default budget."""
    for _ in range(5):
        assert (await client.get("/health/live")).status_code == 200
