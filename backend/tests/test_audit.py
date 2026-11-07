"""Audit log service and admin endpoints."""

from __future__ import annotations

import uuid

from app.db.models.audit import AuditLog
from app.services.audit import ACTION_LOGIN_SUCCESS, AuditService
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from tests.conftest import TEST_PASSWORD, login


async def test_audit_service_records_and_lists(db_session: AsyncSession) -> None:
    service = AuditService(db_session)
    for index in range(5):
        await service.record(
            "test.action",
            actor_id=f"user-{index % 2}",
            actor_email=f"user{index}@divu.ai",
            outcome="success" if index % 2 == 0 else "failure",
            resource_type="thing",
            resource_id=f"thing-{index}",
            message="recorded",
            metadata={"index": index},
        )

    page = await service.list_recent(page=1, page_size=3)
    assert page.total == 5
    assert len(page.items) == 3
    assert page.pages == 2

    filtered = await service.list_recent(action="test.action", outcome="failure")
    assert filtered.total == 2
    assert all(row.outcome == "failure" for row in filtered.items)

    by_actor = await service.list_recent(actor_id="user-1")
    assert by_actor.total == 2


async def test_successful_login_is_audited(client: AsyncClient, db_session: AsyncSession) -> None:
    email = f"audit-{uuid.uuid4().hex[:8]}@divu.ai"
    await client.post("/api/v1/auth/register", json={"email": email, "password": TEST_PASSWORD})
    await login(client, email, TEST_PASSWORD)

    rows = (
        (await db_session.execute(select(AuditLog).where(AuditLog.action == ACTION_LOGIN_SUCCESS)))
        .scalars()
        .all()
    )
    assert len(rows) == 1
    assert rows[0].actor_email == email
    assert rows[0].outcome == "success"


async def test_admin_can_query_audit_log(client: AsyncClient, admin_client: dict) -> None:
    response = await client.get("/api/v1/audit?page_size=10", headers=admin_client["headers"])
    assert response.status_code == 200
    body = response.json()
    assert body["page_size"] == 10
    assert body["total"] >= 1

    filtered = await client.get(
        "/api/v1/audit?action=auth.login.success", headers=admin_client["headers"]
    )
    assert filtered.status_code == 200
    assert all(item["action"] == "auth.login.success" for item in filtered.json()["items"])


async def test_audit_actions_catalog(client: AsyncClient, admin_client: dict) -> None:
    response = await client.get("/api/v1/audit/actions", headers=admin_client["headers"])
    assert response.status_code == 200
    actions = response.json()["actions"]
    assert "auth.login.success" in actions
    assert "security.permission_denied" in actions


async def test_audit_is_admin_only(client: AsyncClient, user_client: dict) -> None:
    assert (await client.get("/api/v1/audit", headers=user_client["headers"])).status_code == 403
