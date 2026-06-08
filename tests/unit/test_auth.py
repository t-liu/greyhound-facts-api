"""Unit tests for the auth dependency."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.core.auth import _resolve_api_key, require_admin
from app.core.config import Settings


def _settings(
    admin_api_key: str | None = None,
    secrets_manager_secret_name: str | None = None,
) -> Settings:
    return Settings(
        app_env="local",
        dynamodb_table_name="test-table",
        admin_api_key=admin_api_key,
        secrets_manager_secret_name=secrets_manager_secret_name,
        aws_default_region="us-east-1",
    )


# ── _resolve_api_key ──────────────────────────────────────────────────────────


class TestResolveApiKey:
    def setup_method(self) -> None:
        import app.core.auth as auth_module
        auth_module._cached_api_key = None  # noqa: SLF001

    def test_returns_env_key(self) -> None:
        s = _settings(admin_api_key="my-secret-key")
        result = _resolve_api_key(s)
        assert result == "my-secret-key"

    def test_caches_result(self) -> None:
        s = _settings(admin_api_key="cached-key")
        _resolve_api_key(s)
        # Second call should use cache; even if settings changes it's cached.
        s2 = _settings(admin_api_key="different-key")
        result = _resolve_api_key(s2)
        assert result == "cached-key"

    def test_raises_without_any_config(self) -> None:
        s = _settings()
        with pytest.raises(RuntimeError, match="No API key configured"):
            _resolve_api_key(s)

    def test_fetches_from_secrets_manager(self) -> None:
        s = _settings(secrets_manager_secret_name="my/secret")
        with patch("app.core.auth._fetch_secret", return_value="sm-key") as mock_fetch:
            result = _resolve_api_key(s)
        mock_fetch.assert_called_once_with("my/secret", "us-east-1")
        assert result == "sm-key"


# ── require_admin ─────────────────────────────────────────────────────────────


class TestRequireAdmin:
    def setup_method(self) -> None:
        import app.core.auth as auth_module
        auth_module._cached_api_key = None  # noqa: SLF001

    @pytest.mark.asyncio
    async def test_valid_key_passes(self) -> None:
        s = _settings(admin_api_key="good-key")
        # Should not raise
        await require_admin(api_key="good-key", settings=s)

    @pytest.mark.asyncio
    async def test_missing_key_raises_401(self) -> None:
        s = _settings(admin_api_key="good-key")
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(api_key=None, settings=s)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_wrong_key_raises_403(self) -> None:
        s = _settings(admin_api_key="good-key")
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(api_key="wrong-key", settings=s)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_misconfigured_raises_503(self) -> None:
        s = _settings()  # No key configured
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(api_key="any-key", settings=s)
        assert exc_info.value.status_code == 503
