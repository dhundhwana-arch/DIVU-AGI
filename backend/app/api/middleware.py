"""HTTP middleware: request context (id + logging) and rate limiting."""

from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from app.core.config import Settings, get_settings
from app.core.errors import _envelope
from app.core.ids import new_id
from app.core.logging import get_logger
from app.security.rate_limit import RateLimiter, client_key

logger = get_logger(__name__)

RATE_LIMIT_EXEMPT_PATHS = ("/health", "/metrics", "/docs", "/openapi.json", "/redoc")
REQUEST_ID_HEADER = "X-Request-ID"


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assigns a request id, binds it to logs, and emits one access log line."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER.lower()) or new_id()
        request.state.request_id = request_id
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = int((time.perf_counter() - started) * 1000)
            logger.exception(
                "request_failed",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                duration_ms=duration_ms,
            )
            raise
        duration_ms = int((time.perf_counter() - started) * 1000)
        response.headers[REQUEST_ID_HEADER] = request_id
        response.headers["X-Response-Time-Ms"] = str(duration_ms)
        logger.info(
            "request_completed",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            client=client_key(request),
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window limiter with a stricter bucket for authentication endpoints."""

    def __init__(
        self, app: ASGIApp, limiter: RateLimiter, settings: Settings | None = None
    ) -> None:
        super().__init__(app)
        self._limiter = limiter
        self._settings = settings or get_settings()

    def _limits_for(self, path: str) -> tuple[int, int]:
        prefix = self._settings.api_v1_prefix
        if path.startswith(f"{prefix}/auth"):
            return (
                self._settings.auth_rate_limit_requests,
                self._settings.auth_rate_limit_window_seconds,
            )
        return (self._settings.rate_limit_requests, self._settings.rate_limit_window_seconds)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        settings = self._settings
        path = request.url.path
        if not settings.rate_limit_enabled or path.startswith(RATE_LIMIT_EXEMPT_PATHS):
            return await call_next(request)

        limit, window = self._limits_for(path)
        key = f"{client_key(request)}:{path.split('?')[0]}"
        result = await self._limiter.check(key, limit, window)
        if not result.allowed:
            request_id = getattr(request.state, "request_id", None)
            response = JSONResponse(
                status_code=429,
                content=_envelope(
                    "rate_limited",
                    "Too many requests. Please slow down and try again later.",
                    {"limit": limit, "window_seconds": window},
                    request_id,
                ),
            )
            response.headers["Retry-After"] = str(result.retry_after)
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = "0"
            if request_id:
                response.headers[REQUEST_ID_HEADER] = request_id
            return response

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(result.remaining)
        return response
