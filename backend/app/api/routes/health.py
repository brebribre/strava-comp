from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.deps import get_db
from app.schemas.health import HealthResponse
from app.services import health as health_service

router = APIRouter(tags=["system"])


@router.get(
    "/health",
    summary="Health check",
    description="Returns 200 only if the API is up **and** a `SELECT 1` against Postgres succeeds.",
    response_model=HealthResponse,
)
def health(session: Annotated[Session, Depends(get_db)]) -> HealthResponse:
    health_service.check_database(session)
    return HealthResponse(status="ok", database="ok")
