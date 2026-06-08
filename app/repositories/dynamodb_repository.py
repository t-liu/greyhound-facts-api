"""DynamoDB repository using a single-table design.

Table schema
────────────
PK              SK           Description
fact#<uuid>     METADATA     A greyhound fact item
config          INDEX        Metadata item tracking the fact index

The INDEX item stores a String Set of all fact IDs so random selection is
O(1) without a Scan.  Writes use ``ADD`` / ``DELETE`` update expressions
which are idempotent and free of read-then-write race conditions.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any, NoReturn

import boto3
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

from app.core.config import Settings
from app.core.exceptions import FactNotFoundError, NoFactsAvailableError, RepositoryError

logger = logging.getLogger(__name__)

_PK_PREFIX = "fact#"
_METADATA_SK = "METADATA"
_INDEX_PK = "config"
_INDEX_SK = "INDEX"


def _pk(fact_id: str) -> str:
    return f"{_PK_PREFIX}{fact_id}"


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


class DynamoDBRepository:
    """All DynamoDB operations for greyhound facts."""

    def __init__(self, settings: Settings) -> None:
        kwargs: dict[str, Any] = {"region_name": settings.aws_default_region}
        if settings.dynamodb_endpoint_url:
            kwargs["endpoint_url"] = settings.dynamodb_endpoint_url

        dynamodb = boto3.resource("dynamodb", **kwargs)
        self._table = dynamodb.Table(settings.dynamodb_table_name)
        self._table_name = settings.dynamodb_table_name
        self._client = boto3.client("dynamodb", **kwargs)

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_fact(self, fact_id: str) -> dict[str, Any]:
        """Return the raw item dict for a fact, or raise FactNotFoundError."""
        try:
            response = self._table.get_item(Key={"PK": _pk(fact_id), "SK": _METADATA_SK})
        except ClientError as exc:
            self._handle_client_error(exc, "get_fact")

        item = response.get("Item")
        if not item:
            raise FactNotFoundError(fact_id)
        return item

    def get_random_fact_id(self) -> str:
        """
        Pick a random fact ID from the INDEX item in O(1).
        Raises NoFactsAvailableError if the index is empty.
        """
        import random  # noqa: PLC0415 — defer import to keep module-level clean

        try:
            response = self._table.get_item(Key={"PK": _INDEX_PK, "SK": _INDEX_SK})
        except ClientError as exc:
            self._handle_client_error(exc, "get_random_fact_id")

        item = response.get("Item")
        ids: set[str] = item.get("fact_ids", set()) if item else set()

        if not ids:
            raise NoFactsAvailableError

        return random.choice(list(ids))  # noqa: S311

    # ── Write ─────────────────────────────────────────────────────────────────

    def put_fact(self, fact_id: str, item: dict[str, Any]) -> None:
        """
        Persist a new fact and atomically add its ID to the INDEX.
        Uses a DynamoDB transaction to keep the fact and index consistent.
        Raises RepositoryError if the fact already exists.
        """
        now = _now_iso()
        ddb_item = {
            "PK": {"S": _pk(fact_id)},
            "SK": {"S": _METADATA_SK},
            "fact_id": {"S": fact_id},
            "created_at": {"S": now},
            "updated_at": {"S": now},
            "text": {"S": item["text"]},
        }
        if "tags" in item:
            ddb_item["tags"] = {"L": [{"S": t} for t in item["tags"]]}
        if "source" in item:
            ddb_item["source"] = {"S": item["source"]}

        try:
            self._client.transact_write_items(
                TransactItems=[
                    {
                        "Put": {
                            "TableName": self._table_name,
                            "Item": ddb_item,
                            "ConditionExpression": "attribute_not_exists(PK)",
                        }
                    },
                    {
                        "Update": {
                            "TableName": self._table_name,
                            "Key": {
                                "PK": {"S": _INDEX_PK},
                                "SK": {"S": _INDEX_SK},
                            },
                            "UpdateExpression": "ADD fact_ids :ids",
                            "ExpressionAttributeValues": {
                                ":ids": {"SS": [fact_id]},
                            },
                        }
                    },
                ]
            )
        except ClientError as exc:
            code = exc.response["Error"]["Code"]
            if code == "TransactionCanceledException":
                reasons = exc.response.get("CancellationReasons", [])
                if reasons and reasons[0].get("Code") == "ConditionalCheckFailed":
                    raise RepositoryError(f"Fact '{fact_id}' already exists.") from exc
            self._handle_client_error(exc, "put_fact")

    def update_fact(self, fact_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        """
        Apply a partial update to an existing fact.
        Raises FactNotFoundError if it doesn't exist.
        Returns the updated item.
        """
        if not updates:
            return self.get_fact(fact_id)

        now = _now_iso()
        updates["updated_at"] = now

        set_expr = "SET " + ", ".join(f"#{k} = :{k}" for k in updates)
        expr_names = {f"#{k}": k for k in updates}
        expr_values = {f":{k}": v for k, v in updates.items()}

        try:
            response = self._table.update_item(
                Key={"PK": _pk(fact_id), "SK": _METADATA_SK},
                UpdateExpression=set_expr,
                ExpressionAttributeNames=expr_names,
                ExpressionAttributeValues=expr_values,
                ConditionExpression=Attr("PK").exists(),
                ReturnValues="ALL_NEW",
            )
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise FactNotFoundError(fact_id) from exc
            self._handle_client_error(exc, "update_fact")

        return response["Attributes"]

    def delete_fact(self, fact_id: str) -> None:
        """
        Delete a fact and atomically remove its ID from the INDEX.
        Uses a DynamoDB transaction to keep the fact and index consistent.
        Raises FactNotFoundError if it doesn't exist.
        """
        try:
            self._client.transact_write_items(
                TransactItems=[
                    {
                        "Delete": {
                            "TableName": self._table_name,
                            "Key": {
                                "PK": {"S": _pk(fact_id)},
                                "SK": {"S": _METADATA_SK},
                            },
                            "ConditionExpression": "attribute_exists(PK)",
                        }
                    },
                    {
                        "Update": {
                            "TableName": self._table_name,
                            "Key": {
                                "PK": {"S": _INDEX_PK},
                                "SK": {"S": _INDEX_SK},
                            },
                            "UpdateExpression": "DELETE fact_ids :ids",
                            "ExpressionAttributeValues": {
                                ":ids": {"SS": [fact_id]},
                            },
                        }
                    },
                ]
            )
        except ClientError as exc:
            code = exc.response["Error"]["Code"]
            if code == "TransactionCanceledException":
                reasons = exc.response.get("CancellationReasons", [])
                if reasons and reasons[0].get("Code") == "ConditionalCheckFailed":
                    raise FactNotFoundError(fact_id) from exc
            self._handle_client_error(exc, "delete_fact")

    # ── Error handling ────────────────────────────────────────────────────────

    def _handle_client_error(self, exc: ClientError, operation: str) -> NoReturn:
        logger.error(
            "DynamoDB %s error: %s",
            operation,
            exc.response["Error"],
            extra={"operation": operation},
        )
        raise RepositoryError(f"DynamoDB error during {operation}.") from exc
