"""Admin API key authentication dependency."""

from __future__ import annotations

import logging

import boto3
from botocore.exceptions import ClientError
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# Module-level cache so the secret is only fetched once per cold start.
_cached_api_key: str | None = None


def _fetch_secret(secret_name: str, region: str) -> str:
    """Retrieve the API key from AWS Secrets Manager."""
    client = boto3.client("secretsmanager", region_name=region)
    try:
        response = client.get_secret_value(SecretId=secret_name)
    except ClientError as exc:
        logger.error("Failed to fetch secret '%s': %s", secret_name, exc)
        raise RuntimeError(f"Could not retrieve secret '{secret_name}'.") from exc
    return response["SecretString"]


def _resolve_api_key(settings: Settings) -> str:
    """
    Return the admin API key, with the following priority:
      1. Module-level cache (populated after first successful fetch).
      2. ``ADMIN_API_KEY`` env var (local dev override).
      3. AWS Secrets Manager (prod).
    """
    global _cached_api_key  # noqa: PLW0603

    if _cached_api_key is not None:
        return _cached_api_key

    if settings.admin_api_key:
        _cached_api_key = settings.admin_api_key
        return _cached_api_key

    if settings.secrets_manager_secret_name:
        _cached_api_key = _fetch_secret(
            settings.secrets_manager_secret_name,
            settings.aws_default_region,
        )
        return _cached_api_key

    raise RuntimeError(
        "No API key configured. Set ADMIN_API_KEY or SECRETS_MANAGER_SECRET_NAME."
    )


async def require_admin(
    api_key: str | None = Security(API_KEY_HEADER),
    settings: Settings = Depends(get_settings),
) -> None:
    """FastAPI dependency: raise 401 if the X-API-Key header is missing or wrong."""
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    try:
        expected = _resolve_api_key(settings)
    except RuntimeError as exc:
        logger.error("Auth configuration error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable.",
        ) from exc

    if api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key.",
        )
