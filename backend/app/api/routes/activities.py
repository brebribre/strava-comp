from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentAthlete, DbSession
from app.config import get_settings
from app.infra.strava import StravaError
from app.schemas.activities import SyncResult
from app.services import activities as activities_service
from app.services.errors import ReauthorizationRequired

router = APIRouter(tags=["activities"])


@router.post(
    "/activities/sync",
    summary="Sync my activities from Strava",
    description=(
        "Pulls your activities from the last `days` days and upserts them. Runs automatically "
        "in the background at login; this endpoint re-runs it on demand."
    ),
    response_model=SyncResult,
)
def sync_activities(
    athlete: CurrentAthlete,
    session: DbSession,
    days: int = Query(default=None, ge=1, le=365, description="Defaults to BACKFILL_DAYS."),
) -> SyncResult:
    days = days or get_settings().backfill_days
    since = datetime.now(UTC) - timedelta(days=days)
    try:
        saved = activities_service.sync_athlete_activities(session, athlete.athlete_id, since)
    except ReauthorizationRequired:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Strava access was revoked — please reconnect",
        ) from None
    except StravaError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from None
    return SyncResult(athlete_id=athlete.athlete_id, since=since, activities_saved=saved)
