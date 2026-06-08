"""Public facts router: health check + read endpoints."""

from __future__ import annotations

from importlib.metadata import version as pkg_version

from fastapi import APIRouter, Depends, Path

from app.core.config import Settings, get_settings
from app.models.response import FactResponse, HealthResponse
from app.repositories.dynamodb_repository import DynamoDBRepository
from app.services.fact_service import FactService

router = APIRouter()


# ── Dependency ────────────────────────────────────────────────────────────────


def get_fact_service(settings: Settings = Depends(get_settings)) -> FactService:
    repo = DynamoDBRepository(settings)
    return FactService(repo)


# ── Routes ────────────────────────────────────────────────────────────────────


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    tags=["Health"],
)
async def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    """Return service health status, version, and deployment environment."""
    try:
        app_version = pkg_version("greyhound-facts-api")
    except Exception:  # noqa: BLE001
        app_version = "dev"
    return HealthResponse(
        status="ok",
        version=app_version,
        environment=settings.app_env,
    )


@router.get(
    "/facts/random",
    response_model=FactResponse,
    summary="Get a random greyhound fact",
    tags=["Facts"],
)
async def get_random_fact(
    service: FactService = Depends(get_fact_service),
) -> FactResponse:
    """Return a randomly selected greyhound fact."""
    return service.get_random_fact()


@router.get(
    "/facts/{fact_id}",
    response_model=FactResponse,
    summary="Get a fact by ID",
    tags=["Facts"],
)
async def get_fact(
    fact_id: str = Path(..., description="UUID of the greyhound fact."),
    service: FactService = Depends(get_fact_service),
) -> FactResponse:
    """Return a specific greyhound fact by its UUID."""
    return service.get_fact(fact_id)
