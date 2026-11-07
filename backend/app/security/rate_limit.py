"""Sliding-window rate limiting.

Backends:
* ``memory`` — per-process deque, correct for single-instance dev/test deployments.
* ``redis``  — shared counters for multi-instance production.

Availability choice: if Redis is unreachable the limiter **fails open** (requests are allowed and
the failure is logged). A rate limiter outage must not become a platform outage; the reverse
risk is mitigated by per-user quotas and audit logging (see SECURITY_GUIDE.md, risk S8).
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from contextlib import suppress
from dataclasses import dataclass
from typing import Protocol

from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    retry_after: int  # seconds; 0 when allowed


class RateLimiter(Protocol):
    async def check(self, key: str, limit: int, window_seconds: int) -> RateLimitResult: ...
    async def reset(self, key: str) -> None: ...
    async def close(self) -> None: ...


class InMemoryRateLimiter:
    """Sliding-window limiter. Not shared across processes."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def check(self, key: str, limit: int, window_seconds: int) -> RateLimitResult:
        now = time.monotonic()
        async with self._lock:
            bucket = self._hits[key]
            while bucket and now - bucket[0] >= window_seconds:
                bucket.popleft()
            if len(bucket) >= limit:
                retry_after = max(1, int(window_seconds - (now - bucket[0])) + 1)
                return RateLimitResult(False, limit, 0, retry_after)
            bucket.append(now)
            self._gc(now, window_seconds)
            return RateLimitResult(True, limit, max(0, limit - len(bucket)), 0)

    def _gc(self, now: float, window_seconds: int) -> None:
        if len(self._hits) <= 10_000:
            return
        for key in [k for k, v in self._hits.items() if not v or now - v[0] >= window_seconds]:
            self._hits.pop(key, None)

    async def reset(self, key: str) -> None:
        async with self._lock:
            self._hits.pop(key, None)

    async def close(self) -> None:
        async with self._lock:
            self._hits.clear()


class RedisRateLimiter:
    """Fixed-window counter in Redis. Shared across instances."""

    def __init__(self, redis_url: str, *, prefix: str = "divu:rl") -> None:
        import redis.asyncio as aioredis  # imported lazily: Redis is optional at runtime

        self._prefix = prefix
        self._client = aioredis.from_url(redis_url, decode_responses=True)

    async def check(self, key: str, limit: int, window_seconds: int) -> RateLimitResult:
        redis_key = f"{self._prefix}:{key}"
        try:
            count = await self._client.incr(redis_key)
            if count == 1:
                await self._client.expire(redis_key, window_seconds)
            ttl = await self._client.ttl(redis_key)
            retry_after = int(ttl) if ttl and ttl > 0 else window_seconds
            if count > limit:
                return RateLimitResult(False, limit, 0, max(1, retry_after))
            return RateLimitResult(True, limit, max(0, limit - int(count)), 0)
        except Exception as exc:  # fail open
            logger.warning("rate_limit_backend_error", error=str(exc), key=key)
            return RateLimitResult(True, limit, limit, 0)

    async def reset(self, key: str) -> None:
        try:
            await self._client.delete(f"{self._prefix}:{key}")
        except Exception as exc:  # pragma: no cover - network dependent
            logger.warning("rate_limit_reset_error", error=str(exc))

    async def close(self) -> None:
        with suppress(Exception):  # pragma: no cover - network dependent
            await self._client.aclose()


def build_rate_limiter(settings: Settings | None = None) -> RateLimiter:
    settings = settings or get_settings()
    if settings.cache_backend == "redis":
        return RedisRateLimiter(settings.redis_url)
    return InMemoryRateLimiter()


def client_key(request: object) -> str:
    """Best-effort client identifier from a Starlette/FastAPI request."""
    headers = getattr(request, "headers", {}) or {}
    forwarded = headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    client = getattr(request, "client", None)
    return getattr(client, "host", "unknown") or "unknown"
