from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status

from app.api.deps import CurrentAthlete, DbSession
from app.config import get_settings
from app.infra.strava import StravaError
from app.schemas.activities import SyncResult
from app.schemas.activity_detail import ActivityDetail
from app.services import activities as activities_service
from app.services import activity_detail as detail_service
from app.services.errors import NotAGroupMember, ReauthorizationRequired

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
    background: BackgroundTasks,
    days: int = Query(
        default=None,
        ge=1,
        le=3650,
        description=(
            "How far back to pull. Defaults to BACKFILL_DAYS. Large values are fine — the "
            "list endpoint returns 200 activities per request, so even years cost a handful "
            "of calls against Strava's 200-per-15-minutes budget."
        ),
    ),
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

    # The sync stores summary payloads; top up the newest few with full detail
    # (description, photos, splits) in the background so the feed has something to show.
    background.add_task(detail_service.enrich_recent_in_background, athlete.athlete_id)

    return SyncResult(athlete_id=athlete.athlete_id, since=since, activities_saved=saved)


@router.get(
    "/activities/{activity_id}",
    summary="Activity detail",
    description=(
        "Full detail for one activity: description, calories, splits and the GPS polyline. "
        "Visible to the owner and to anyone sharing a group with them. The first request "
        "enriches the stored record from Strava's detailed endpoint and caches it."
    ),
    response_model=ActivityDetail,
)
def activity_detail(
    activity_id: int,
    athlete: CurrentAthlete,
    session: DbSession,
) -> ActivityDetail:
    try:
        return detail_service.activity_detail(session, activity_id, athlete.athlete_id)
    except NotAGroupMember:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't share a group with this athlete",
        ) from None
    except LookupError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Activity not found"
        ) from None
