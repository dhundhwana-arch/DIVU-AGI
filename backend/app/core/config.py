"""Typed application configuration.

All configuration comes from ``DIVU_``-prefixed environment variables (optionally via a
``.env`` file). There are no hard-coded secrets in this repository: every credential is read
from the environment and is redacted from logs by :mod:`app.core.logging`.
"""

from __future__ import annotations

import secrets
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BackendRoot = Path(__file__).resolve().parents[2]


def _split_list(value: Any) -> list[str]:
    """Accept ``"a,b"`` or ``'["a","b"]'`` from the environment."""
    if value is None or value == "":
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return list(value)


class Settings(BaseSettings):
    """Runtime configuration. Validated once at startup; immutable afterwards."""

    model_config = SettingsConfigDict(
        env_prefix="DIVU_",
        env_file=(".env",),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---------------- Application ----------------
    app_name: str = "DIVU AI"
    app_env: Literal["development", "test", "staging", "production"] = "development"
    version: str = "0.1.0"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    docs_url: str | None = "/docs"

    # ---------------- Security ----------------
    secret_key: str = ""
    encryption_key: str = ""
    jwt_algorithm: str = "HS256"
    access_token_ttl_seconds: int = 900
    refresh_token_ttl_seconds: int = 60 * 60 * 24 * 14
    password_min_length: int = 12
    password_hash_iterations: int = 600_000
    allow_public_registration: bool = True
    max_failed_logins: int = 8
    lockout_seconds: int = 900

    # ---------------- Database ----------------
    database_url: str = "sqlite+aiosqlite:///./.data/divu.db"
    db_echo: bool = False
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # ---------------- Cache / rate limiting ----------------
    cache_backend: Literal["memory", "redis"] = "memory"
    redis_url: str = "redis://localhost:6379/0"
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60
    auth_rate_limit_requests: int = 10
    auth_rate_limit_window_seconds: int = 60

    # ---------------- Object storage ----------------
    object_storage_backend: Literal["local", "s3"] = "local"
    object_storage_path: str = "./.data/objects"
    s3_bucket: str = ""
    s3_region: str = ""
    s3_endpoint_url: str = ""

    # ---------------- HTTP ----------------
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )
    cors_origin_regex: str = ""

    # ---------------- Logging ----------------
    log_level: str = "INFO"
    log_format: Literal["console", "json"] = "console"
    log_prompt_content: bool = False  # opt-in only: never log user content by default

    # ---------------- AI providers (values only; never committed) ----------------
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    anthropic_api_key: str = ""
    anthropic_base_url: str = "https://api.anthropic.com"
    google_api_key: str = ""
    default_provider: str = "mock"

    # ---------------- Feature flags (phases gate their own features) ----------------
    enable_chat: bool = False
    enable_memory: bool = False
    enable_rag: bool = False
    enable_agents: bool = False
    enable_addons: bool = False
    enable_multimodal: bool = False
    enable_multi_agent: bool = False

    # ---------------- Validators ----------------
    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors(cls, value: Any) -> Any:
        return _split_list(value)

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalize_database_url(cls, value: str) -> str:
        url = str(value).strip()
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://") and "+asyncpg" not in url:
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif url.startswith("sqlite://") and "+aiosqlite" not in url:
            url = url.replace("sqlite://", "sqlite+aiosqlite://", 1)
        return url

    @model_validator(mode="after")
    def _validate_security_requirements(self) -> Settings:
        if self.is_production:
            if not self.secret_key or len(self.secret_key) < 32:
                raise ValueError(
                    "DIVU_SECRET_KEY must be set to a random string of at least 32 characters "
                    "when DIVU_APP_ENV=production."
                )
            if not self.encryption_key:
                raise ValueError(
                    "DIVU_ENCRYPTION_KEY (a Fernet key) is required when "
                    "DIVU_APP_ENV=production."
                )
            if self.debug or self.docs_url:
                raise ValueError(
                    "DIVU_DEBUG must be false and DIVU_DOCS_URL must be empty in production."
                )
            if self.allow_public_registration:
                raise ValueError("DIVU_ALLOW_PUBLIC_REGISTRATION must be false in production.")
        if not self.secret_key:
            # Ephemeral dev/test key: sessions do not survive a restart, which is intended.
            if self.app_env in {"development", "test"}:
                object.__setattr__(self, "secret_key", secrets.token_urlsafe(48))
            else:
                raise ValueError("DIVU_SECRET_KEY is required outside development/test.")
        return self

    # ---------------- Derived helpers ----------------
    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_testing(self) -> bool:
        return self.app_env == "test"

    @property
    def db_is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def db_is_postgres(self) -> bool:
        return self.database_url.startswith("postgresql")

    @property
    def object_storage_dir(self) -> Path:
        path = Path(self.object_storage_path)
        if not path.is_absolute():
            path = BackendRoot / path
        return path

    @property
    def resolved_features(self) -> dict[str, bool]:
        return {
            "chat": self.enable_chat,
            "memory": self.enable_memory,
            "rag": self.enable_rag,
            "agents": self.enable_agents,
            "addons": self.enable_addons,
            "multimodal": self.enable_multimodal,
            "multi_agent": self.enable_multi_agent,
        }

    def secret_values(self) -> list[str]:
        """Values that must never appear in a log line, response or report."""
        candidates = [
            self.secret_key,
            self.encryption_key,
            self.openai_api_key,
            self.anthropic_api_key,
            self.google_api_key,
        ]
        return [value for value in candidates if value and len(value) >= 8]

    def configured_providers(self) -> list[str]:
        found = []
        if self.openai_api_key:
            found.append("openai")
        if self.anthropic_api_key:
            found.append("anthropic")
        if self.google_api_key:
            found.append("google")
        found.append("mock")  # always available; keeps the platform runnable offline
        return found

    def safe_dict(self) -> dict[str, Any]:
        """Configuration view safe to expose over the API (no secrets)."""
        data = self.model_dump()
        redacted = {
            "secret_key",
            "encryption_key",
            "openai_api_key",
            "anthropic_api_key",
            "google_api_key",
        }
        for key in list(data):
            if key in redacted:
                data[key] = "***redacted***" if data[key] else ""
        return data


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings singleton. Tests reset it with ``get_settings.cache_clear()``."""
    return Settings()


def reload_settings() -> Settings:
    get_settings.cache_clear()
    return get_settings()
