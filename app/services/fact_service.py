"""Business logic for greyhound facts."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from app.models.request import CreateFactRequest, UpdateFactRequest
from app.models.response import FactResponse
from app.repositories.dynamodb_repository import DynamoDBRepository

logger = logging.getLogger(__name__)


def _item_to_response(item: dict) -> FactResponse:  # type: ignore[type-arg]
    """Map a raw DynamoDB item to a FactResponse."""
    return FactResponse(
        id=item["fact_id"],
        text=item["text"],
        source=item.get("source"),
        tags=list(item.get("tags", [])),
        created_at=datetime.fromisoformat(item["created_at"]),
        updated_at=datetime.fromisoformat(item["updated_at"]),
    )


class FactService:
    """Orchestrates fact CRUD and random selection via the repository."""

    def __init__(self, repository: DynamoDBRepository) -> None:
        self._repo = repository

    # ── Public reads ──────────────────────────────────────────────────────────

    def get_fact(self, fact_id: str) -> FactResponse:
        """Return a fact by ID. Raises FactNotFoundError if absent."""
        item = self._repo.get_fact(fact_id)
        return _item_to_response(item)

    def get_random_fact(self) -> FactResponse:
        """
        Return a randomly selected fact.
        Raises NoFactsAvailableError when the table is empty.
        """
        fact_id = self._repo.get_random_fact_id()
        return self.get_fact(fact_id)

    # ── Admin writes ──────────────────────────────────────────────────────────

    def create_fact(self, payload: CreateFactRequest) -> FactResponse:
        """Create a new fact, returning the persisted record."""
        fact_id = str(uuid.uuid4())

        item: dict = {
            "text": payload.text,
            "tags": payload.tags,
        }
        if payload.source is not None:
            item["source"] = payload.source

        self._repo.put_fact(fact_id, item)

        logger.info("Created fact '%s'.", fact_id)
        # Re-fetch to get the stored timestamps and guarantee consistency.
        return self.get_fact(fact_id)

    def update_fact(self, fact_id: str, payload: UpdateFactRequest) -> FactResponse:
        """Apply a partial update to an existing fact."""
        updates: dict = {}
        if payload.text is not None:
            updates["text"] = payload.text
        if payload.source is not None:
            updates["source"] = payload.source
        if payload.tags is not None:
            updates["tags"] = payload.tags

        item = self._repo.update_fact(fact_id, updates)
        logger.info("Updated fact '%s'.", fact_id)
        return _item_to_response(item)

    def delete_fact(self, fact_id: str) -> None:
        """Delete a fact by ID. Raises FactNotFoundError if absent."""
        self._repo.delete_fact(fact_id)
        logger.info("Deleted fact '%s'.", fact_id)
