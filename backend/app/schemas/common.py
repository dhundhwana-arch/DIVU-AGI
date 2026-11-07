"""Shared API contracts."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ORMModel(BaseModel):
    """Base that allows constructing responses directly from ORM objects."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class Page(BaseModel, Generic[T]):
    """Standard list envelope: pagination is explicit for every collection endpoint.

    ``T`` may be a Pydantic model (API responses) or an ORM class (service-layer results),
    so arbitrary types are allowed and validated by ``isinstance``.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    items: list[T] = Field(default_factory=list)
    page: int = 1
    page_size: int = 50
    total: int = 0

    @property
    def pages(self) -> int:
        if self.page_size <= 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size


class MessageResponse(BaseModel):
    message: str
    detail: str | None = None


class HealthComponent(BaseModel):
    name: str
    healthy: bool
    detail: str = ""
    latency_ms: int = 0


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)
