"""Pydantic v2 response models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class FactResponse(BaseModel):
    """A single greyhound fact returned by the API."""

    id: str = Field(..., description="Unique fact identifier (UUID).")
    text: str = Field(..., description="The greyhound fact text.")
    source: str | None = Field(default=None, description="Attribution or source URL.")
    tags: list[str] = Field(default_factory=list, description="Categorisation tags.")
    created_at: datetime = Field(..., description="ISO-8601 creation timestamp (UTC).")
    updated_at: datetime = Field(..., description="ISO-8601 last-update timestamp (UTC).")


class HealthResponse(BaseModel):
    """Response body for GET /v1/health."""

    status: str = Field(default="ok", description="Service status.")
    version: str = Field(..., description="Application version string.")
    environment: str = Field(..., description="Deployment environment (local/dev/prod).")
