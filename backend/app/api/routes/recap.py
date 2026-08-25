from fastapi import APIRouter, Query

from app.api.deps import CurrentAthlete, DbSession
from app.schemas.recap import RecapOverview, SportRecap
from app.services import recap as recap_service

router = APIRouter(prefix="/recap", tags=["recap"])


@router.get(
    "",
    summary="Per-sport recap for the logged-in athlete",
    description=(
        "Totals for each sport over the window, each next to the equivalent previous period "
        "so growth is visible. Personal — group membership is irrelevant here."
    ),
    response_model=RecapOverview,
)
def get_overview(
    athlete: CurrentAthlete,
    session: DbSession,
    days: int = Query(default=365, ge=7, le=3650),
) -> RecapOverview:
    return recap_service.overview(session, athlete.athlete_id, days)


@router.get(
    "/{sport_type}",
    summary="One sport in depth",
    description="Month-by-month trend, personal bests and consistency for a single sport.",
    response_model=SportRecap,
)
def get_sport(
    sport_type: str,
    athlete: CurrentAthlete,
    session: DbSession,
    months: int = Query(default=12, ge=1, le=120),
) -> SportRecap:
    return recap_service.sport_recap(session, athlete.athlete_id, sport_type, months)
