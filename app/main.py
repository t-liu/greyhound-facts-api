"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin, facts
from app.core.config import get_settings
from app.core.exceptions import (
    FactNotFoundError,
    NoFactsAvailableError,
    RepositoryError,
    fact_not_found_handler,
    generic_error_handler,
    no_facts_available_handler,
    repository_error_handler,
)
from app.core.logging import configure_logging
from app.core.middleware import RequestIDMiddleware

settings = get_settings()
configure_logging(settings.log_level)


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    _app = FastAPI(
        title="Greyhound Facts API",
        description="A production-grade serverless API serving facts about Greyhound dogs.",
        version="1.0.0",
        docs_url="/v1/docs",
        redoc_url="/v1/redoc",
        openapi_url="/v1/openapi.json",
    )

    # ── Middleware ────────────────────────────────────────────────────────────
    _app.add_middleware(RequestIDMiddleware)
    _app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ───────────────────────────────────────────────────────────────
    _app.include_router(facts.router, prefix="/v1")
    _app.include_router(admin.router, prefix="/v1/admin")

    # ── Exception handlers ────────────────────────────────────────────────────
    _app.add_exception_handler(FactNotFoundError, fact_not_found_handler)  # type: ignore[arg-type]
    _app.add_exception_handler(NoFactsAvailableError, no_facts_available_handler)  # type: ignore[arg-type]
    _app.add_exception_handler(RepositoryError, repository_error_handler)  # type: ignore[arg-type]
    _app.add_exception_handler(Exception, generic_error_handler)  # type: ignore[arg-type]

    return _app


app = create_app()
