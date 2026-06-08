"""Pydantic v2 error models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Machine-readable error code with a human-readable description."""

    code: str = Field(..., description="Stable error code string (e.g. FACT_NOT_FOUND).")
    detail: str = Field(..., description="Human-readable description of the error.")


class ErrorResponse(BaseModel):
    """Standard error envelope returned on all 4xx/5xx responses."""

    error: ErrorDetail
    request_id: str = Field(..., description="The X-Request-ID for this request.")
