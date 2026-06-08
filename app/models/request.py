"""Pydantic v2 request models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CreateFactRequest(BaseModel):
    """Payload for POST /v1/admin/facts."""

    text: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="The greyhound fact text.",
        examples=["Greyhounds can reach speeds of up to 45 mph."],
    )
    source: str | None = Field(
        default=None,
        max_length=200,
        description="Optional attribution or source URL.",
        examples=["American Kennel Club"],
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Optional categorisation tags.",
        examples=[["speed", "physiology"]],
    )


class UpdateFactRequest(BaseModel):
    """Payload for PUT /v1/admin/facts/{id}. All fields optional (partial update)."""

    text: str | None = Field(
        default=None,
        min_length=10,
        max_length=500,
        description="Updated fact text.",
    )
    source: str | None = Field(
        default=None,
        max_length=200,
        description="Updated source.",
    )
    tags: list[str] | None = Field(
        default=None,
        description="Replacement tag list.",
    )
