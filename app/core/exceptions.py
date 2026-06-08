"""Custom exceptions and FastAPI exception handlers."""

from __future__ import annotations

from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.models.error import ErrorDetail, ErrorResponse

# ── Domain exceptions ─────────────────────────────────────────────────────────


class FactNotFoundError(Exception):
    """Raised when a requested fact does not exist in the store."""

    def __init__(self, fact_id: str) -> None:
        self.fact_id = fact_id
        super().__init__(f"Fact '{fact_id}' not found.")


class NoFactsAvailableError(Exception):
    """Raised when a random fact is requested but the table is empty."""


class RepositoryError(Exception):
    """Raised on unexpected DynamoDB errors."""


# ── FastAPI exception handlers ────────────────────────────────────────────────


def _error_response(request: Request, status_code: int, code: str, detail: str) -> JSONResponse:
    request_id: str = getattr(request.state, "request_id", "unknown")
    body = ErrorResponse(
        error=ErrorDetail(code=code, detail=detail),
        request_id=request_id,
    )
    return JSONResponse(status_code=status_code, content=body.model_dump())


async def fact_not_found_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, FactNotFoundError)
    return _error_response(
        request,
        status.HTTP_404_NOT_FOUND,
        "FACT_NOT_FOUND",
        str(exc),
    )


async def no_facts_available_handler(request: Request, exc: Exception) -> JSONResponse:
    return _error_response(
        request,
        status.HTTP_404_NOT_FOUND,
        "NO_FACTS_AVAILABLE",
        "No facts are currently available.",
    )


async def repository_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return _error_response(
        request,
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "REPOSITORY_ERROR",
        "A database error occurred. Please try again later.",
    )


async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return _error_response(
        request,
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "INTERNAL_ERROR",
        "An unexpected error occurred.",
    )
