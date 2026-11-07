"""Role-based access control (acceptance tests A3, A4)."""

from __future__ import annotations

import uuid

from app.db.models.audit import AuditLog
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from tests.conftest import TEST_PASSWORD


async def test_admin_can_list_users(client: AsyncClient, admin_client: dict) -> None:
    response = await client.get("/api/v1/users", headers=admin_client["headers"])
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] >= 1
    assert any(user["email"] == admin_client["email"] for user in body["items"])


async def test_ordinary_user_is_denied(client: AsyncClient, user_client: dict) -> None:
    response = await client.get("/api/v1/users", headers=user_client["headers"])
    assert response.status_code == 403
    error = response.json()["error"]
    assert error["code"] == "permission_denied"
    assert error["details"]["required_roles"] == ["admin"]


async def test_denied_access_is_audited(
    client: AsyncClient, user_client: dict, db_session: AsyncSession
) -> None:
    await client.get("/api/v1/users", headers=user_client["headers"])
    rows = (
        (
            await db_session.execute(
                select(AuditLog).where(AuditLog.action == "security.permission_denied")
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1
    assert rows[0].outcome == "denied"
    assert rows[0].metadata_json["required_roles"] == ["admin"]


async def test_unauthenticated_access_returns_401(client: AsyncClient) -> None:
    response = await client.get("/api/v1/users")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_required"


async def test_admin_can_change_roles_and_status(client: AsyncClient, admin_client: dict) -> None:
    email = f"target-{uuid.uuid4().hex[:8]}@divu.ai"
    created = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": TEST_PASSWORD}
    )
    user_id = created.json()["id"]

    roles = await client.post(
        f"/api/v1/users/{user_id}/roles",
        headers=admin_client["headers"],
        json={"roles": ["developer"]},
    )
    assert roles.status_code == 200
    assert roles.json()["roles"] == ["developer"]

    status = await client.patch(
        f"/api/v1/users/{user_id}/status",
        headers=admin_client["headers"],
        json={"is_active": False},
    )
    assert status.status_code == 200
    assert status.json()["is_active"] is False

    # Deactivated users cannot log in.
    login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": TEST_PASSWORD}
    )
    assert login.status_code == 401


async def test_unknown_role_is_rejected(client: AsyncClient, admin_client: dict) -> None:
    email = f"roles-{uuid.uuid4().hex[:8]}@divu.ai"
    created = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": TEST_PASSWORD}
    )
    user_id = created.json()["id"]
    response = await client.post(
        f"/api/v1/users/{user_id}/roles",
        headers=admin_client["headers"],
        json={"roles": ["wizard"]},
    )
    assert response.status_code == 422
    assert "known_roles" in response.json()["error"]["details"]


async def test_roles_catalog(client: AsyncClient, admin_client: dict) -> None:
    response = await client.get("/api/v1/users/roles", headers=admin_client["headers"])
    assert response.status_code == 200
    names = {role["name"] for role in response.json()["items"]}
    assert {"admin", "user", "developer", "viewer"} <= names


async def test_admin_config_view_is_redacted(client: AsyncClient, admin_client: dict) -> None:
    response = await client.get("/api/v1/system/config", headers=admin_client["headers"])
    assert response.status_code == 200
    body = response.json()
    assert body["secret_key"] == "***redacted***"
    assert body["encryption_key"] in {"***redacted***", ""}


async def test_admin_cannot_delete_self(client: AsyncClient, admin_client: dict) -> None:
    me = await client.get("/api/v1/system/me", headers=admin_client["headers"])
    user_id = me.json()["user_id"]
    response = await client.delete(f"/api/v1/users/{user_id}", headers=admin_client["headers"])
    assert response.status_code == 422
