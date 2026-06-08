"""Unit tests for FactService."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import FactNotFoundError, NoFactsAvailableError
from app.models.request import CreateFactRequest, UpdateFactRequest
from app.models.response import FactResponse
from app.services.fact_service import FactService


def _make_item(
    fact_id: str = "abc-123",
    text: str = "Greyhounds are fast.",
    source: str | None = "AKC",
    tags: list[str] | None = None,
) -> dict:
    now = datetime.now(tz=UTC).isoformat()
    return {
        "fact_id": fact_id,
        "text": text,
        "source": source,
        "tags": tags or ["speed"],
        "created_at": now,
        "updated_at": now,
    }


@pytest.fixture()
def mock_repo() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def service(mock_repo: MagicMock) -> FactService:
    return FactService(repository=mock_repo)


# ── get_fact ──────────────────────────────────────────────────────────────────


class TestGetFact:
    def test_returns_fact_response(self, service: FactService, mock_repo: MagicMock) -> None:
        item = _make_item()
        mock_repo.get_fact.return_value = item

        result = service.get_fact("abc-123")

        assert isinstance(result, FactResponse)
        assert result.id == "abc-123"
        assert result.text == "Greyhounds are fast."
        mock_repo.get_fact.assert_called_once_with("abc-123")

    def test_propagates_not_found(self, service: FactService, mock_repo: MagicMock) -> None:
        mock_repo.get_fact.side_effect = FactNotFoundError("missing")

        with pytest.raises(FactNotFoundError):
            service.get_fact("missing")


# ── get_random_fact ───────────────────────────────────────────────────────────


class TestGetRandomFact:
    def test_returns_random_fact(self, service: FactService, mock_repo: MagicMock) -> None:
        item = _make_item()
        mock_repo.get_random_fact_id.return_value = "abc-123"
        mock_repo.get_fact.return_value = item

        result = service.get_random_fact()

        assert result.id == "abc-123"

    def test_propagates_no_facts_available(self, service: FactService, mock_repo: MagicMock) -> None:
        mock_repo.get_random_fact_id.side_effect = NoFactsAvailableError()

        with pytest.raises(NoFactsAvailableError):
            service.get_random_fact()


# ── create_fact ───────────────────────────────────────────────────────────────


class TestCreateFact:
    def test_creates_fact_and_returns_response(
        self, service: FactService, mock_repo: MagicMock
    ) -> None:
        payload = CreateFactRequest(
            text="Greyhounds can see 270 degrees.",
            source="AKC",
            tags=["vision"],
        )
        item = _make_item(text=payload.text, source="AKC", tags=["vision"])
        mock_repo.get_fact.return_value = item

        result = service.create_fact(payload)

        mock_repo.put_fact.assert_called_once()
        assert result.text == "Greyhounds can see 270 degrees."

    def test_creates_fact_without_source(
        self, service: FactService, mock_repo: MagicMock
    ) -> None:
        payload = CreateFactRequest(text="Greyhounds are gentle giants.")
        item = _make_item(text=payload.text, source=None, tags=[])
        mock_repo.get_fact.return_value = item

        service.create_fact(payload)

        call_args = mock_repo.put_fact.call_args
        stored_item = call_args[0][1]
        assert "source" not in stored_item

    def test_uses_uuid_for_fact_id(self, service: FactService, mock_repo: MagicMock) -> None:
        payload = CreateFactRequest(text="Greyhounds love to sleep all day long.")
        item = _make_item()
        mock_repo.get_fact.return_value = item

        with patch("app.services.fact_service.uuid.uuid4", return_value="fixed-uuid"):
            service.create_fact(payload)

        call_args = mock_repo.put_fact.call_args
        assert call_args[0][0] == "fixed-uuid"


# ── update_fact ───────────────────────────────────────────────────────────────


class TestUpdateFact:
    def test_updates_provided_fields(self, service: FactService, mock_repo: MagicMock) -> None:
        updated_item = _make_item(text="Updated text for this fact.")
        mock_repo.update_fact.return_value = updated_item

        payload = UpdateFactRequest(text="Updated text for this fact.")
        result = service.update_fact("abc-123", payload)

        mock_repo.update_fact.assert_called_once_with("abc-123", {"text": "Updated text for this fact."})
        assert result.text == "Updated text for this fact."

    def test_empty_payload_does_not_call_update(
        self, service: FactService, mock_repo: MagicMock
    ) -> None:
        item = _make_item()
        mock_repo.get_fact.return_value = item
        mock_repo.update_fact.return_value = item

        payload = UpdateFactRequest()
        service.update_fact("abc-123", payload)

        mock_repo.update_fact.assert_called_once_with("abc-123", {})

    def test_propagates_not_found(self, service: FactService, mock_repo: MagicMock) -> None:
        mock_repo.update_fact.side_effect = FactNotFoundError("missing")

        with pytest.raises(FactNotFoundError):
            service.update_fact("missing", UpdateFactRequest(text="New text for testing here."))


# ── delete_fact ───────────────────────────────────────────────────────────────


class TestDeleteFact:
    def test_calls_repo_delete(self, service: FactService, mock_repo: MagicMock) -> None:
        service.delete_fact("abc-123")
        mock_repo.delete_fact.assert_called_once_with("abc-123")

    def test_propagates_not_found(self, service: FactService, mock_repo: MagicMock) -> None:
        mock_repo.delete_fact.side_effect = FactNotFoundError("missing")

        with pytest.raises(FactNotFoundError):
            service.delete_fact("missing")
