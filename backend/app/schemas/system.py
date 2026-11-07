"""System / health contracts."""

from __future__ import annotations

from datetime import datetime

from app.schemas.common import HealthComponent, ORMModel
from pydantic import Field


class BrandInfo(ORMModel):
    name: str
    tagline: str
    founder_name: str
    founder_title: str


class SystemInfoResponse(ORMModel):
    brand: BrandInfo
    app: str
    version: str
    environment: str
    phase: str
    features: dict[str, bool] = Field(default_factory=dict)
    providers: list[str] = Field(default_factory=list)
    database: str
    cache: str
    storage: str
    capabilities: dict[str, bool] = Field(default_factory=dict)
    server_time: datetime


class HealthResponse(ORMModel):
    status: str
    version: str
    environment: str
    components: list[HealthComponent] = Field(default_factory=list)


class ReadyResponse(HealthResponse):
    ready: bool
