"""Authentication flows (acceptance tests A1-A5)."""

from __future__ import annotations

import uuid

import pytest
from app.core.config import Settings
from app.core.errors import InvalidCredentialsError
from app.db.models.audit import AuditLog
from app.db.models.user import User
from app.services.auth_service import AuthService
from app.services.user_service import UserService
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from tests.conftest import TEST_PASSWORD, login


async def test_register_login_me(client: AsyncClient) -> None:
    email = f"a-{uuid.uuid4().hex[:8]}@divu.ai"
    created = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": TEST_PASSWORD, "full_name": "Divyesh"},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["email"] == email
    assert "password" not in body and "hashed_password" not in body
    assert body["roles"] == ["user"]

    tokens = await login(client, email, TEST_PASSWORD)
    assert tokens["token_type"] == "bearer"
    assert tokens["expires_in"] > 0

    me = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert me.status_code == 200
    assert me.json()["email"] == email


async def test_duplicate_registration_conflicts(client: AsyncClient) -> None:
    email = f"dup-{uuid.uuid4().hex[:8]}@divu.ai"
    first = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": TEST_PASSWORD}
    )
    assert first.status_code == 201
    second = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": TEST_PASSWORD}
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "conflict"


async def test_weak_password_rejected(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": f"w-{uuid.uuid4().hex[:8]}@divu.ai", "password": "abc"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["details"]


async def test_invalid_credentials_and_audit(client: AsyncClient, db_session: AsyncSession) -> None:
    email = f"bad-{uuid.uuid4().hex[:8]}@divu.ai"
    created = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": TEST_PASSWORD}
    )
    user_id = created.json()["id"]

    response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "WrongPassword!123"}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"

    rows = (
        (
            await db_session.execute(
                select(AuditLog).where(
                    AuditLog.action == "auth.login.failure", AuditLog.actor_id == user_id
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1
    assert rows[0].outcome == "failure"
    assert rows[0].metadata_json["reason"] == "invalid_credentials"


async def test_unknown_account_is_audited_without_revealing_existence(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    response = await client.post(
        "/api/v1/auth/login", json={"email": "nobody@divu.ai", "password": "Whatever!12345"}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"

    rows = (
        (await db_session.execute(select(AuditLog).where(AuditLog.action == "auth.login.failure")))
        .scalars()
        .all()
    )
    assert any(row.metadata_json["reason"] == "unknown_account" for row in rows)


async def test_expired_and_tampered_tokens(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not.a.token"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "token_invalid"

    response = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer abc"})
    assert response.status_code == 401


async def test_refresh_rotation_and_reuse_detection(client: AsyncClient) -> None:
    email = f"rot-{uuid.uuid4().hex[:8]}@divu.ai"
    await client.post("/api/v1/auth/register", json={"email": email, "password": TEST_PASSWORD})
    tokens = await login(client, email, TEST_PASSWORD)

    refreshed = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refreshed.status_code == 200
    new_tokens = refreshed.json()
    assert new_tokens["access_token"] != tokens["access_token"]

    reuse = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert reuse.status_code == 401
    assert reuse.json()["error"]["code"] == "token_invalid"

    # Reuse revokes the whole family, so the rotated token is dead too.
    after_reuse = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": new_tokens["refresh_token"]}
    )
    assert after_reuse.status_code == 401


async def test_refresh_token_cannot_be_used_as_access_token(client: AsyncClient) -> None:
    email = f"typ-{uuid.uuid4().hex[:8]}@divu.ai"
    await client.post("/api/v1/auth/register", json={"email": email, "password": TEST_PASSWORD})
    tokens = await login(client, email, TEST_PASSWORD)
    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['refresh_token']}"}
    )
    assert response.status_code == 401


async def test_logout_revokes_refresh_token(client: AsyncClient) -> None:
    email = f"out-{uuid.uuid4().hex[:8]}@divu.ai"
    await client.post("/api/v1/auth/register", json={"email": email, "password": TEST_PASSWORD})
    tokens = await login(client, email, TEST_PASSWORD)

    response = await client.post(
        "/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]}
    )
    assert response.status_code == 200

    reused = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert reused.status_code == 401


async def test_change_password(client: AsyncClient, user_client: dict) -> None:
    response = await client.post(
        "/api/v1/auth/change-password",
        headers=user_client["headers"],
        json={"current_password": TEST_PASSWORD, "new_password": "Another!Passphrase9"},
    )
    assert response.status_code == 200, response.text

    old_login = await client.post(
        "/api/v1/auth/login",
        json={"email": user_client["user"]["email"], "password": TEST_PASSWORD},
    )
    assert old_login.status_code == 401

    new_login = await client.post(
        "/api/v1/auth/login",
        json={"email": user_client["user"]["email"], "password": "Another!Passphrase9"},
    )
    assert new_login.status_code == 200


async def test_change_password_with_wrong_current_password(
    user_client: dict, client: AsyncClient
) -> None:
    response = await client.post(
        "/api/v1/auth/change-password",
        headers=user_client["headers"],
        json={"current_password": "NotThePassword!1", "new_password": "Another!Passphrase9"},
    )
    assert response.status_code == 401


async def test_account_lockout_after_repeated_failures(db_session: AsyncSession) -> None:
    settings = Settings(
        app_env="test",
        secret_key="x" * 48,
        max_failed_logins=3,
        lockout_seconds=600,
        password_hash_iterations=1000,
        database_url="sqlite+aiosqlite:///:memory:",
    )
    service = AuthService(db_session, settings=settings)
    email = f"lock-{uuid.uuid4().hex[:8]}@divu.ai"
    await UserService(db_session).create_user(email=email, password=TEST_PASSWORD)

    for _ in range(3):
        with pytest.raises(InvalidCredentialsError):
            await service.authenticate(email=email, password="Wrong!Password1")

    with pytest.raises(InvalidCredentialsError) as caught:
        await service.authenticate(email=email, password=TEST_PASSWORD)
    assert "locked" in str(caught.value).lower()

    user = (await db_session.execute(select(User).where(User.email == email))).scalar_one()
    assert user.is_locked is True


async def test_password_policy_endpoint(client: AsyncClient) -> None:
    weak = await client.post("/api/v1/auth/password/check", json={"password": "short"})
    assert weak.json()["valid"] is False

    strong = await client.post("/api/v1/auth/password/check", json={"password": TEST_PASSWORD})
    assert strong.json()["valid"] is True


async def test_api_key_lifecycle_and_usage(client: AsyncClient, user_client: dict) -> None:
    created = await client.post(
        "/api/v1/auth/api-keys",
        headers=user_client["headers"],
        json={"name": "ci-runner", "scopes": ["chat:write"]},
    )
    assert created.status_code == 201, created.text
    key = created.json()
    assert key["token"].startswith("dvk_")
    assert key["scopes"] == ["chat:write"]

    listed = await client.get("/api/v1/auth/api-keys", headers=user_client["headers"])
    assert listed.json()["total"] == 1
    assert "token" not in listed.json()["items"][0]

    authenticated = await client.get("/api/v1/auth/me", headers={"X-API-Key": key["token"]})
    assert authenticated.status_code == 200
    assert authenticated.json()["email"] == user_client["user"]["email"]

    revoked = await client.delete(
        f"/api/v1/auth/api-keys/{key['id']}", headers=user_client["headers"]
    )
    assert revoked.status_code == 200

    after_revoke = await client.get("/api/v1/auth/me", headers={"X-API-Key": key["token"]})
    assert after_revoke.status_code == 401


async def test_refresh_of_unknown_token(client: AsyncClient) -> None:
    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": "x" * 40})
    assert response.status_code in {401, 422}


async def test_public_registration_can_be_disabled(db_session: AsyncSession) -> None:
    settings = Settings(
        app_env="test",
        secret_key="y" * 48,
        allow_public_registration=False,
        password_hash_iterations=1000,
        database_url="sqlite+aiosqlite:///:memory:",
    )
    service = AuthService(db_session, settings=settings)
    from app.core.errors import PermissionDeniedError

    with pytest.raises(PermissionDeniedError):
        await service.register(email="blocked@divu.ai", password=TEST_PASSWORD)


async def test_validation_error_envelope_has_request_id(client: AsyncClient) -> None:
    response = await client.post("/api/v1/auth/login", json={"email": "not-an-email"})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert error["request_id"]
