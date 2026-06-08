"""Admin facts router: CRUD endpoints (require X-API-Key)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Path, status

from app.core.auth import require_admin
from app.core.config import Settings, get_settings
from app.models.request import CreateFactRequest, UpdateFactRequest
from app.models.response import FactResponse
from app.repositories.dynamodb_repository import DynamoDBRepository
from app.services.fact_service import FactService

router = APIRouter(dependencies=[Depends(require_admin)])


# ── Dependency ────────────────────────────────────────────────────────────────


def get_fact_service(settings: Settings = Depends(get_settings)) -> FactService:
    repo = DynamoDBRepository(settings)
    return FactService(repo)


# ── Routes ────────────────────────────────────────────────────────────────────


@router.post(
    "/facts",
    response_model=FactResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new fact",
    tags=["Admin"],
)
async def create_fact(
    payload: CreateFactRequest,
    service: FactService = Depends(get_fact_service),
) -> FactResponse:
    """Create a new greyhound fact. Requires ``X-API-Key`` header."""
    return service.create_fact(payload)


@router.put(
    "/facts/{fact_id}",
    response_model=FactResponse,
    summary="Update a fact",
    tags=["Admin"],
)
async def update_fact(
    payload: UpdateFactRequest,
    fact_id: str = Path(..., description="UUID of the fact to update."),
    service: FactService = Depends(get_fact_service),
) -> FactResponse:
    """Partially update a greyhound fact. Requires ``X-API-Key`` header."""
    return service.update_fact(fact_id, payload)


@router.delete(
    "/facts/{fact_id}",
    response_model=None,
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a fact",
    tags=["Admin"],
)
async def delete_fact(
    fact_id: str = Path(..., description="UUID of the fact to delete."),
    service: FactService = Depends(get_fact_service),
) -> None:
    """Delete a greyhound fact. Requires ``X-API-Key`` header."""
    service.delete_fact(fact_id)
