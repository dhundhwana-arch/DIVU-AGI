"""System introspection: health probes, capability detection, brand/system info."""

from __future__ import annotations

import time
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app import __brand__, __founder__, __tagline__, __version__
from app.core.config import Settings, get_settings
from app.core.ids import utcnow
from app.schemas.common import HealthComponent
from app.schemas.system import BrandInfo, SystemInfoResponse

CURRENT_PHASE = "phase-1-foundation"


class SystemService:
    """Read-only diagnostics. Never returns secrets (see ``Settings.safe_dict``)."""

    def __init__(
        self, session: AsyncSession | None = None, settings: Settings | None = None
    ) -> None:
        self._session = session
        self._settings = settings or get_settings()

    # ---------------- Probes ----------------
    async def check_database(self) -> HealthComponent:
        if self._session is None:
            return HealthComponent(name="database", healthy=False, detail="no session")
        started = time.perf_counter()
        try:
            await self._session.execute(text("SELECT 1"))
            detail = "postgres" if self._settings.db_is_postgres else "sqlite"
            return HealthComponent(
                name="database",
                healthy=True,
                detail=detail,
                latency_ms=int((time.perf_counter() - started) * 1000),
            )
        except Exception as exc:  # pragma: no cover - exercised when the DB is down
            return HealthComponent(
                name="database",
                healthy=False,
                detail=f"{type(exc).__name__}: {exc}",
                latency_ms=int((time.perf_counter() - started) * 1000),
            )

    async def check_cache(self) -> HealthComponent:
        started = time.perf_counter()
        backend = self._settings.cache_backend
        if backend != "redis":
            return HealthComponent(
                name="cache",
                healthy=True,
                detail=f"memory (in-process, backend={backend})",
                latency_ms=0,
            )
        try:  # pragma: no cover - requires Redis
            import redis.asyncio as aioredis

            client = aioredis.from_url(self._settings.redis_url)
            await client.ping()
            await client.aclose()
            return HealthComponent(
                name="cache",
                healthy=True,
                detail="redis",
                latency_ms=int((time.perf_counter() - started) * 1000),
            )
        except Exception as exc:
            return HealthComponent(
                name="cache",
                healthy=False,
                detail=f"redis unavailable: {exc}",
                latency_ms=int((time.perf_counter() - started) * 1000),
            )

    def check_storage(self) -> HealthComponent:
        if self._settings.object_storage_backend != "local":
            return HealthComponent(
                name="object_storage",
                healthy=bool(self._settings.s3_bucket),
                detail=f"s3 bucket={'set' if self._settings.s3_bucket else 'missing'}",
            )
        try:
            directory = self._settings.object_storage_dir
            directory.mkdir(parents=True, exist_ok=True)
            probe = directory / ".write_probe"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return HealthComponent(name="object_storage", healthy=True, detail=f"local:{directory}")
        except Exception as exc:  # pragma: no cover - filesystem permissions
            return HealthComponent(
                name="object_storage", healthy=False, detail=f"local storage error: {exc}"
            )

    async def readiness(self) -> tuple[bool, list[HealthComponent]]:
        components = [await self.check_database(), self.check_storage(), await self.check_cache()]
        return all(component.healthy for component in components), components

    # ---------------- Info ----------------
    async def detect_capabilities(self) -> dict[str, bool]:
        """Feature detection used by the UI to hide what the deployment cannot do."""
        vector_extension = False
        if self._session is not None and self._settings.db_is_postgres:
            try:  # pragma: no cover - requires Postgres
                result = await self._session.execute(
                    text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
                )
                vector_extension = result.scalar_one_or_none() is not None
            except Exception:
                vector_extension = False
        return {
            "vector_search": vector_extension,
            "redis_cache": self._settings.cache_backend == "redis",
            "object_storage": self._settings.object_storage_backend == "local"
            or bool(self._settings.s3_bucket),
            "provider_configured": len(
                [p for p in self._settings.configured_providers() if p != "mock"]
            )
            > 0,
        }

    async def info(self) -> SystemInfoResponse:
        return SystemInfoResponse(
            brand=BrandInfo(
                name=__brand__,
                tagline=__tagline__,
                founder_name=__founder__,
                founder_title="Founder & Creator",
            ),
            app=self._settings.app_name,
            version=__version__,
            environment=self._settings.app_env,
            phase=CURRENT_PHASE,
            features=self._settings.resolved_features,
            providers=self._settings.configured_providers(),
            database="postgres" if self._settings.db_is_postgres else "sqlite",
            cache=self._settings.cache_backend,
            storage=self._settings.object_storage_backend,
            capabilities=await self.detect_capabilities(),
            server_time=utcnow(),
        )

    def config_view(self) -> dict[str, Any]:
        """Redacted configuration snapshot for administrators."""
        return self._settings.safe_dict()
