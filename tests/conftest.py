"""Shared pytest fixtures."""

from __future__ import annotations

import os
from collections.abc import Generator
from unittest.mock import patch

import boto3
import pytest
from fastapi.testclient import TestClient
from moto import mock_aws

from app.core.config import Settings

# ── Env defaults so Settings() works without a .env file ─────────────────────
os.environ.setdefault("ADMIN_API_KEY", "test-api-key")
os.environ.setdefault("DYNAMODB_TABLE_NAME", "greyhound-facts-test")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
# Moto requires fake credentials
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("AWS_SECURITY_TOKEN", "testing")
os.environ.setdefault("AWS_SESSION_TOKEN", "testing")

TABLE_NAME = "greyhound-facts-test"
ADMIN_API_KEY = "test-api-key"


@pytest.fixture()
def test_settings() -> Settings:
    """Return a Settings instance wired for tests."""
    return Settings(
        app_env="local",
        dynamodb_table_name=TABLE_NAME,
        admin_api_key=ADMIN_API_KEY,
        aws_default_region="us-east-1",
    )


@pytest.fixture()
def aws_mock() -> Generator[None, None, None]:
    """Activate moto AWS mocking for the duration of a test."""
    with mock_aws():
        yield


@pytest.fixture()
def dynamodb_table(aws_mock: None, test_settings: Settings):  # type: ignore[no-untyped-def]
    """Create a mocked DynamoDB table and return the boto3 Table resource."""
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table = dynamodb.create_table(
        TableName=TABLE_NAME,
        KeySchema=[
            {"AttributeName": "PK", "KeyType": "HASH"},
            {"AttributeName": "SK", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "SK", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    table.wait_until_exists()
    return table


@pytest.fixture()
def test_client(aws_mock: None, dynamodb_table) -> TestClient:  # type: ignore[no-untyped-def]
    """Return a FastAPI TestClient with mocked AWS and patched settings."""
    # Reset the auth cache between tests
    import app.core.auth as auth_module
    from app.core.config import get_settings
    from app.main import create_app
    auth_module._cached_api_key = None  # noqa: SLF001

    _app = create_app()

    with patch("app.core.config.get_settings", return_value=test_settings):
        # Override the dependency in the app
        _app.dependency_overrides[get_settings] = lambda: Settings(
            app_env="local",
            dynamodb_table_name=TABLE_NAME,
            admin_api_key=ADMIN_API_KEY,
            aws_default_region="us-east-1",
        )
        yield TestClient(_app)
