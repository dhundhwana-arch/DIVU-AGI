"""Encrypted credential vault (acceptance test A8)."""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

SECRET = "EXAMPLE-CREDENTIAL-VALUE-12345"


async def test_credentials_are_stored_encrypted_and_masked(
    client: AsyncClient, user_client: dict, db_session: AsyncSession
) -> None:
    created = await client.post(
        "/api/v1/security/credentials",
        headers=user_client["headers"],
        json={"provider": "openai", "label": "personal", "value": SECRET},
    )
    assert created.status_code == 200, created.text
    credential_id = created.json()["id"]
    assert SECRET not in created.json()["masked_value"]
    assert created.json()["masked_value"].endswith("2345")

    rows = (
        await db_session.execute(
            text("SELECT encrypted_value FROM provider_credentials WHERE id = :id").bindparams(
                id=credential_id
            )
        )
    ).all()
    assert len(rows) == 1
    assert SECRET not in rows[0][0]
    assert rows[0][0].startswith("enc:v1:")

    listed = await client.get("/api/v1/security/credentials", headers=user_client["headers"])
    assert listed.status_code == 200
    assert listed.json()["items"][0]["masked_value"].endswith("2345")

    revealed = await client.post(
        f"/api/v1/security/credentials/{credential_id}/reveal", headers=user_client["headers"]
    )
    assert revealed.status_code == 200
    assert revealed.json()["value"] == SECRET

    deleted = await client.delete(
        f"/api/v1/security/credentials/{credential_id}", headers=user_client["headers"]
    )
    assert deleted.status_code == 200
    assert (
        await client.get("/api/v1/security/credentials", headers=user_client["headers"])
    ).json()["items"] == []


async def test_credentials_are_private_to_their_owner(
    client: AsyncClient, user_client: dict, admin_client: dict
) -> None:
    created = await client.post(
        "/api/v1/security/credentials",
        headers=user_client["headers"],
        json={"provider": "anthropic", "label": "team", "value": SECRET},
    )
    credential_id = created.json()["id"]
    response = await client.post(
        f"/api/v1/security/credentials/{credential_id}/reveal", headers=admin_client["headers"]
    )
    assert response.status_code == 404


async def test_credential_endpoints_require_authentication(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/security/credentials")).status_code == 401
