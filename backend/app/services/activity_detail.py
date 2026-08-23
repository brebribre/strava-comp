"""Single-activity detail, enriched from Strava on demand."""

import logging
from typing import Any

from sqlmodel import Session, select

from app.infra import strava
from app.infra.db import engine
from app.models import Activity, Athlete, GroupMembership
from app.schemas.activity_detail import ActivityDetail, Split
from app.services.activities import save_activities_to_db
from app.services.errors import AthleteNotFound, NotAGroupMember, ReauthorizationRequired
from app.services.tokens import get_valid_access_token

logger = logging.getLogger(__name__)

# Strava marks fully-detailed payloads with resource_state 3; list responses are 2.
DETAILED_RESOURCE_STATE = 3


def shares_group(session: Session, athlete_a: int, athlete_b: int) -> bool:
    """True if both athletes belong to at least one group together."""
    their_groups = select(GroupMembership.group_id).where(GroupMembership.athlete_id == athlete_b)
    return (
        session.exec(
            select(GroupMembership)
            .where(GroupMembership.athlete_id == athlete_a)
            .where(GroupMembership.group_id.in_(their_groups))
        ).first()
        is not None
    )


def primary_photo(payload: dict[str, Any] | None) -> str | None:
    """Largest available URL for the activity's primary photo, if it has one."""
    urls = (((payload or {}).get("photos") or {}).get("primary") or {}).get("urls") or {}
    if not urls:
        return None
    # Keys are pixel widths as strings; take the largest available.
    widest = max(urls, key=lambda key: int(key) if key.isdigit() else 0)
    return urls[widest]


def _splits(payload: dict[str, Any]) -> list[Split]:
    return [
        Split(
            split=entry.get("split", index + 1),
            distance=entry.get("distance", 0.0),
            moving_time=entry.get("moving_time", 0),
            elevation_difference=entry.get("elevation_difference"),
            average_heartrate=entry.get("average_heartrate"),
        )
        for index, entry in enumerate(payload.get("splits_metric") or [])
    ]


def _enrich(session: Session, activity: Activity) -> tuple[dict[str, Any], bool]:
    """Return the detailed payload, fetching it from Strava the first time it's needed.

    Uses the *owner's* token, not the viewer's — a groupmate has no access to someone
    else's activity, but the owner authorized this app, and membership is checked before
    we get here. The result is cached back into raw_data so this happens once.
    """
    stored = activity.raw_data or {}
    if stored.get("resource_state") == DETAILED_RESOURCE_STATE:
        return stored, True

    try:
        token = get_valid_access_token(session, activity.owner_id)
        payload = strava.fetch_activity(token, activity.id)
    except (ReauthorizationRequired, AthleteNotFound, strava.StravaError) as exc:
        # Fall back to what we already have rather than failing the page.
        logger.warning("could not enrich activity %s: %s", activity.id, exc)
        return stored, False

    save_activities_to_db(session, activity.owner_id, [payload])
    return payload, True


def activity_detail(session: Session, activity_id: int, viewer_id: int) -> ActivityDetail:
    activity = session.get(Activity, activity_id)
    if activity is None:
        raise LookupError(f"no activity {activity_id}")

    if activity.owner_id != viewer_id and not shares_group(session, viewer_id, activity.owner_id):
        raise NotAGroupMember("not in a group with this athlete")

    payload, is_detailed = _enrich(session, activity)
    owner = session.get(Athlete, activity.owner_id)

    # Prefer the full-resolution polyline; fall back to the summary one.
    activity_map = payload.get("map") or {}
    polyline = activity_map.get("polyline") or activity_map.get("summary_polyline") or None

    description = payload.get("description")

    return ActivityDetail(
        activity_id=activity.id,
        athlete_id=activity.owner_id,
        athlete_name=owner.name if owner else "Unknown",
        name=activity.name,
        # Strava returns "" for an empty description; treat that as absent.
        description=description or None,
        sport_type=activity.sport_type,
        start_date=activity.start_date,
        distance=activity.distance or 0.0,
        moving_time=activity.moving_time or 0,
        elapsed_time=activity.elapsed_time or 0,
        total_elevation_gain=activity.total_elevation_gain or 0.0,
        average_heartrate=activity.average_heartrate,
        max_heartrate=activity.max_heartrate,
        calories=payload.get("calories"),
        device_name=payload.get("device_name"),
        polyline=polyline,
        photo_url=primary_photo(payload),
        splits=_splits(payload),
        is_detailed=is_detailed,
    )


def enrich_recent(session: Session, athlete_id: int, limit: int = 10) -> int:
    """Upgrade recent summary-only activities to detailed payloads.

    Backfill and the list endpoint store SummaryActivity, which carries no description,
    calories, splits or photos — so the feed would never show a photo for them. This tops
    up the most recent few, newest first.

    Bounded deliberately: Strava allows 200 requests per 15 minutes and this costs one
    request per activity.
    """
    candidates = session.exec(
        select(Activity)
        .where(Activity.owner_id == athlete_id)
        .order_by(Activity.start_date.desc())
        .limit(limit * 3)
    ).all()

    pending = [
        activity
        for activity in candidates
        if (activity.raw_data or {}).get("resource_state") != DETAILED_RESOURCE_STATE
    ][:limit]
    if not pending:
        return 0

    try:
        token = get_valid_access_token(session, athlete_id)
    except (ReauthorizationRequired, AthleteNotFound) as exc:
        logger.warning("cannot enrich for athlete %s: %s", athlete_id, exc)
        return 0

    enriched = 0
    for activity in pending:
        try:
            payload = strava.fetch_activity(token, activity.id)
        except strava.StravaError as exc:
            # Most likely rate limiting — stop rather than burning the remaining budget.
            logger.warning("enrichment stopped at activity %s: %s", activity.id, exc)
            break
        save_activities_to_db(session, athlete_id, [payload])
        enriched += 1

    logger.info("enriched %s activities for athlete %s", enriched, athlete_id)
    return enriched


def enrich_recent_in_background(athlete_id: int, limit: int = 10) -> None:
    """BackgroundTasks entry point — owns its session, never raises."""
    try:
        with Session(engine) as session:
            enrich_recent(session, athlete_id, limit)
    except Exception:  # noqa: BLE001 - background task must not crash the worker
        logger.exception("unexpected enrichment failure for athlete %s", athlete_id)
