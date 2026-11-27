"""Health check router."""

from fastapi import APIRouter, status
from pydantic import BaseModel

from backend.app.core.config import settings
from backend.app.core.middleware import get_request_id

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    request_id: str


class ReadinessResponse(BaseModel):
    status: str
    version: str
    database: str
    redis: str
    request_id: str


@router.get("/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def health_check() -> dict:
    """Basic liveness health check."""
    return {
        "status": "healthy",
        "version": settings.app_version,
        "environment": settings.environment,
        "request_id": get_request_id(),
    }


@router.get("/health/ready", response_model=ReadinessResponse, status_code=status.HTTP_200_OK)
async def readiness_check() -> dict:
    """Readiness check verifying dependent services (DB, Redis)."""
    # In future phases, actual connection checks for DB and Redis will go here.
    return {
        "status": "ready",
        "version": settings.app_version,
        "database": "connected",
        "redis": "connected",
        "request_id": get_request_id(),
    }