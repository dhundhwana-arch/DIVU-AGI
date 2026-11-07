"""Application error model.

Every failure that reaches a client uses one envelope::

    {"error": {"code", "message", "details", "request_id", "timestamp"}}

Handlers are registered in :func:`app.main.create_app`.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.ids import utcnow


class AppError(Exception):
    """Base class for all expected, structured application errors."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    code: str = "internal_error"
    message: str = "An unexpected error occurred."

    def __init__(
        self,
        message: str | None = None,
        *,
        details: Any = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.message = message or self.message
        self.details = details
        self.headers = headers
        super().__init__(self.message)


class BadRequestError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "bad_request"
    message = "The request could not be understood."


class ValidationFailedError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    code = "validation_error"
    message = "The request payload failed validation."


class AuthenticationError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "authentication_required"
    message = "Authentication is required."
    headers = {"WWW-Authenticate": "Bearer"}


class InvalidCredentialsError(AuthenticationError):
    code = "invalid_credentials"
    message = "Invalid email or password."


class TokenInvalidError(AuthenticationError):
    code = "token_invalid"
    message = "The supplied token is invalid or expired."


class PermissionDeniedError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "permission_denied"
    message = "You do not have permission to perform this action."


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"
    message = "The requested resource was not found."


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "conflict"
    message = "The request conflicts with the current state of the resource."


class RateLimitedError(AppError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    code = "rate_limited"
    message = "Too many requests. Please slow down."

    def __init__(self, retry_after: int, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.headers = {"Retry-After": str(retry_after)}


class DependencyUnavailableError(AppError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "dependency_unavailable"
    message = "A required dependency is currently unavailable."


class ProviderError(AppError):
    status_code = status.HTTP_502_BAD_GATEWAY
    code = "provider_error"
    message = "The AI provider returned an error."


class ResourceLimitError(AppError):
    status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    code = "resource_limit_exceeded"
    message = "The request exceeds a configured resource limit."


class FeatureDisabledError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "feature_disabled"
    message = "This feature is not enabled in the current deployment."


def _envelope(
    code: str,
    message: str,
    details: Any,
    request_id: str | None,
) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details,
            "request_id": request_id,
            "timestamp": utcnow().isoformat().replace("+00:00", "Z"),
        }
    }


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def register_exception_handlers(app: FastAPI) -> None:
    """Attach the handlers that produce the standard error envelope."""

    @app.exception_handler(AppError)
    async def _handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        headers = dict(exc.headers or {})
        if _request_id(request):
            headers.setdefault("X-Request-ID", _request_id(request) or "")
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(exc.code, exc.message, exc.details, _request_id(request)),
            headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {
                "loc": list(error.get("loc", [])),
                "msg": error.get("msg", ""),
                "type": error.get("type", ""),
            }
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_envelope(
                "validation_error", "Request validation failed.", details, _request_id(request)
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope("http_error", str(exc.detail), None, _request_id(request)),
            headers=exc.headers or None,
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        # Logged with a stack trace server-side; the client only ever sees the request id.
        from app.core.logging import get_logger

        get_logger(__name__).exception(
            "unhandled_exception",
            path=request.url.path,
            method=request.method,
            error_type=type(exc).__name__,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_envelope(
                "internal_error",
                "An unexpected error occurred. The incident has been logged.",
                None,
                _request_id(request),
            ),
        )
