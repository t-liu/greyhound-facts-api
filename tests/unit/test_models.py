"""Unit tests for Pydantic request/response/error models."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.models.error import ErrorDetail, ErrorResponse
from app.models.request import CreateFactRequest, UpdateFactRequest
from app.models.response import FactResponse, HealthResponse

# ── CreateFactRequest ─────────────────────────────────────────────────────────


class TestCreateFactRequest:
    def test_valid_minimal(self) -> None:
        req = CreateFactRequest(text="Greyhounds are the fastest dog breed.")
        assert req.source is None
        assert req.tags == []

    def test_valid_full(self) -> None:
        req = CreateFactRequest(
            text="Greyhounds can run 45 mph at full speed.",
            source="AKC",
            tags=["speed"],
        )
        assert req.source == "AKC"
        assert req.tags == ["speed"]

    def test_text_too_short(self) -> None:
        with pytest.raises(ValidationError):
            CreateFactRequest(text="Too short")

    def test_text_too_long(self) -> None:
        with pytest.raises(ValidationError):
            CreateFactRequest(text="x" * 501)

    def test_source_too_long(self) -> None:
        with pytest.raises(ValidationError):
            CreateFactRequest(text="Greyhounds are excellent companions.", source="s" * 201)


# ── UpdateFactRequest ─────────────────────────────────────────────────────────


class TestUpdateFactRequest:
    def test_all_fields_optional(self) -> None:
        req = UpdateFactRequest()
        assert req.text is None
        assert req.source is None
        assert req.tags is None

    def test_partial_update(self) -> None:
        req = UpdateFactRequest(text="Updated greyhound fact text here.")
        assert req.text == "Updated greyhound fact text here."
        assert req.source is None

    def test_text_too_short(self) -> None:
        with pytest.raises(ValidationError):
            UpdateFactRequest(text="Short")


# ── FactResponse ──────────────────────────────────────────────────────────────


class TestFactResponse:
    def test_valid(self) -> None:
        now = datetime.now(tz=UTC)
        resp = FactResponse(
            id="uuid-1",
            text="Greyhounds have low body fat.",
            source=None,
            tags=["physiology"],
            created_at=now,
            updated_at=now,
        )
        assert resp.id == "uuid-1"

    def test_tags_default_empty(self) -> None:
        now = datetime.now(tz=UTC)
        resp = FactResponse(
            id="uuid-1",
            text="Greyhounds have low body fat.",
            created_at=now,
            updated_at=now,
        )
        assert resp.tags == []


# ── HealthResponse ────────────────────────────────────────────────────────────


class TestHealthResponse:
    def test_defaults(self) -> None:
        resp = HealthResponse(version="1.0.0", environment="local")
        assert resp.status == "ok"
        assert resp.version == "1.0.0"


# ── ErrorResponse ─────────────────────────────────────────────────────────────


class TestErrorResponse:
    def test_structure(self) -> None:
        err = ErrorResponse(
            error=ErrorDetail(code="FACT_NOT_FOUND", detail="Fact not found."),
            request_id="req-123",
        )
        dumped = err.model_dump()
        assert dumped["error"]["code"] == "FACT_NOT_FOUND"
        assert dumped["request_id"] == "req-123"
