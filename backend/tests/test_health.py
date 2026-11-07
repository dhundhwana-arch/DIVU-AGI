"""Health, version and system-info endpoints (acceptance tests A12, and §7.1.4/5)."""

from __future__ import annotations

from httpx import AsyncClient


async def test_liveness(client: AsyncClient) -> None:
    response = await client.get("/health/live")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["environment"] == "test"


async def test_readiness_reports_sqlite_and_storage(client: AsyncClient) -> None:
    response = await client.get("/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["ready"] is True
    names = {component["name"] for component in body["components"]}
    assert {"database", "object_storage", "cache"} <= names
    database = next(
        component for component in body["components"] if component["name"] == "database"
    )
    assert database["healthy"] is True
    assert database["detail"] == "sqlite"


async def test_version_endpoint_brands_the_product(client: AsyncClient) -> None:
    response = await client.get("/health/version")
    assert response.status_code == 200
    body = response.json()
    assert body["app"] == "DIVU AI"
    assert body["founder"] == "DIVYESH BAMBHANIYA"


async def test_system_info_contains_brand_features_and_capabilities(client: AsyncClient) -> None:
    response = await client.get("/api/v1/system/info")
    assert response.status_code == 200
    body = response.json()
    assert body["brand"]["founder_name"] == "DIVYESH BAMBHANIYA"
    assert body["brand"]["founder_title"] == "Founder & Creator"
    assert body["brand"]["tagline"] == "Beyond Conversations. Towards Intelligence."
    assert "mock" in body["providers"]
    assert "chat" in body["features"]
    assert body["capabilities"]["vector_search"] is False  # not available on SQLite


async def test_request_id_is_returned(client: AsyncClient) -> None:
    response = await client.get("/health/live")
    assert response.headers["X-Request-ID"]
    assert response.headers["X-Response-Time-Ms"].isdigit()


async def test_rate_limit_headers_present(client: AsyncClient) -> None:
    response = await client.get("/api/v1/system/info")
    assert response.headers["X-RateLimit-Limit"] == "120"
