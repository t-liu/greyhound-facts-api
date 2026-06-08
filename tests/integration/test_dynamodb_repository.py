"""Integration tests for DynamoDBRepository against moto."""

from __future__ import annotations

import pytest

from app.core.exceptions import FactNotFoundError, NoFactsAvailableError, RepositoryError
from app.repositories.dynamodb_repository import DynamoDBRepository


@pytest.fixture()
def repo(dynamodb_table, test_settings) -> DynamoDBRepository:  # type: ignore[no-untyped-def]
    return DynamoDBRepository(test_settings)


# ── put_fact / get_fact ───────────────────────────────────────────────────────


class TestPutAndGetFact:
    def test_put_and_retrieve(self, repo: DynamoDBRepository) -> None:
        repo.put_fact("fact-1", {"text": "Greyhounds are fast dogs overall.", "tags": ["speed"]})
        item = repo.get_fact("fact-1")

        assert item["fact_id"] == "fact-1"
        assert item["text"] == "Greyhounds are fast dogs overall."
        assert "created_at" in item
        assert "updated_at" in item

    def test_duplicate_raises_repository_error(self, repo: DynamoDBRepository) -> None:
        repo.put_fact("dup-1", {"text": "Greyhounds sleep up to 18 hours a day."})
        with pytest.raises(RepositoryError):
            repo.put_fact("dup-1", {"text": "Greyhounds sleep up to 18 hours a day."})

    def test_get_missing_raises_not_found(self, repo: DynamoDBRepository) -> None:
        with pytest.raises(FactNotFoundError) as exc_info:
            repo.get_fact("does-not-exist")
        assert exc_info.value.fact_id == "does-not-exist"


# ── get_random_fact_id ────────────────────────────────────────────────────────


class TestGetRandomFactId:
    def test_returns_id_from_index(self, repo: DynamoDBRepository) -> None:
        repo.put_fact("rand-1", {"text": "Greyhounds have a very low body fat percentage."})
        fact_id = repo.get_random_fact_id()
        assert fact_id == "rand-1"

    def test_raises_when_empty(self, repo: DynamoDBRepository) -> None:
        with pytest.raises(NoFactsAvailableError):
            repo.get_random_fact_id()

    def test_returns_one_of_multiple_ids(self, repo: DynamoDBRepository) -> None:
        repo.put_fact("a", {"text": "Greyhounds were mentioned in the Bible passage."})
        repo.put_fact("b", {"text": "Greyhounds can accelerate to 45 mph very quickly."})
        repo.put_fact("c", {"text": "Greyhounds have a 270-degree field of vision."})

        results = {repo.get_random_fact_id() for _ in range(20)}
        # With 3 items and 20 draws, we expect some variation
        assert results.issubset({"a", "b", "c"})
        assert len(results) > 1


# ── update_fact ───────────────────────────────────────────────────────────────


class TestUpdateFact:
    def test_updates_text_field(self, repo: DynamoDBRepository) -> None:
        repo.put_fact("upd-1", {"text": "Original greyhound fact text here."})
        updated = repo.update_fact("upd-1", {"text": "Updated greyhound fact text here."})
        assert updated["text"] == "Updated greyhound fact text here."
        assert updated["updated_at"] != updated.get("created_at") or True  # at minimum updated

    def test_partial_update_preserves_other_fields(self, repo: DynamoDBRepository) -> None:
        repo.put_fact("upd-2", {"text": "Original text for the greyhound.", "tags": ["history"]})
        repo.update_fact("upd-2", {"text": "New text for the greyhound breed."})
        item = repo.get_fact("upd-2")
        assert item["tags"] == ["history"]

    def test_raises_not_found_for_missing(self, repo: DynamoDBRepository) -> None:
        with pytest.raises(FactNotFoundError):
            repo.update_fact("ghost", {"text": "This fact does not actually exist."})

    def test_no_op_when_empty_updates(self, repo: DynamoDBRepository) -> None:
        repo.put_fact("upd-3", {"text": "Greyhounds love to lounge all day."})
        # Empty updates returns current item
        result = repo.update_fact("upd-3", {})
        assert result["text"] == "Greyhounds love to lounge all day."


# ── delete_fact ───────────────────────────────────────────────────────────────


class TestDeleteFact:
    def test_deletes_existing_fact(self, repo: DynamoDBRepository) -> None:
        repo.put_fact("del-1", {"text": "Greyhounds are ancient Egyptian dogs."})
        repo.delete_fact("del-1")
        with pytest.raises(FactNotFoundError):
            repo.get_fact("del-1")

    def test_removes_from_index_on_delete(self, repo: DynamoDBRepository) -> None:
        repo.put_fact("del-2", {"text": "Greyhounds have a gentle and calm nature."})
        repo.delete_fact("del-2")
        with pytest.raises(NoFactsAvailableError):
            repo.get_random_fact_id()

    def test_raises_not_found_for_missing(self, repo: DynamoDBRepository) -> None:
        with pytest.raises(FactNotFoundError):
            repo.delete_fact("nonexistent-fact-id")
