"""Application configuration via pydantic-settings."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── App ───────────────────────────────────────────────────────────────────
    app_env: Literal["local", "dev", "prod"] = "local"
    log_level: str = "INFO"

    # ── DynamoDB ──────────────────────────────────────────────────────────────
    dynamodb_table_name: str = "greyhound-facts"
    dynamodb_endpoint_url: str | None = None  # None → use AWS default

    # ── Auth ──────────────────────────────────────────────────────────────────
    admin_api_key: str | None = None           # local plaintext override
    secrets_manager_secret_name: str | None = None  # prod: fetch from SM

    # ── AWS ───────────────────────────────────────────────────────────────────
    aws_default_region: str = "us-east-1"

    # ── CORS ──────────────────────────────────────────────────────────────────
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: object) -> object:
        """Accept either a JSON string or a real list."""
        if isinstance(v, str):
            return json.loads(v)
        return v


def get_settings() -> Settings:
    """Return a cached Settings instance (one parse per process)."""
    return _settings


_settings = Settings()
