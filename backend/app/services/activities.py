"""Fetching Strava activities and storing them."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import Session

from app.config import get_settings
from app.infra import strava
from app.infra.db import engine
from app.models import Activity
from app.models.base import utcnow
from app.services.errors import ReauthorizationRequired
from app.services.tokens import get_valid_access_token

logger = logging.getLogger(__name__)

# Columns we refresh when an activity we already have comes back changed
# (renamed, re-uploaded, privacy toggled).
_UPDATABLE = (
    "name",
    "sport_type",
    "distance",
    "moving_time",
    "elapsed_time",
    "total_elevation_gain",
    "average_heartrate",
    "max_heartrate",
    "start_date",
    "raw_data",
)


def _parse_start_date(value: str | None) -> datetime | None:
    if not value:
        return None
    # Strava sends "2026-08-23T08:08:27Z"; fromisoformat wants an explicit offset.
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def to_activity_row(payload: dict[str, Any], owner_id: int) -> dict[str, Any]:
    """Map Strava's activity JSON onto our columns.

    owner_id is passed in rather than read from the payload: the webhook's detailed
    activity and the list endpoint disagree on how the athlete is represented.
    """
    # One timestamp per row: two utcnow() calls would leave created_at and updated_at
    # differing by microseconds on first write, making "never updated" untestable.
    now = utcnow()
    return {
        "id": int(payload["id"]),
        "owner_id": owner_id,
        "name": payload.get("name"),
        # sport_type is the modern field; type is the legacy fallback.
        "sport_type": payload.get("sport_type") or payload.get("type"),
        "distance": payload.get("distance"),
        "moving_time": payload.get("moving_time"),
        "elapsed_time": payload.get("elapsed_time"),
        "total_elevation_gain": payload.get("total_elevation_gain"),
        "average_heartrate": payload.get("average_heartrate"),
        "max_heartrate": payload.get("max_heartrate"),
        "start_date": _parse_start_date(payload.get("start_date")),
        "raw_data": payload,
        # pg_insert bypasses SQLModel's Python-side defaults, so both timestamps are
        # set explicitly here. created_at is left out of the ON CONFLICT update below,
        # so it keeps meaning "when we first saw this activity".
        "created_at": now,
        "updated_at": now,
    }


def save_activities_to_db(session: Session, athlete_id: int, activities: list[dict[str, Any]]) -> int:
    """Upsert activities for one athlete. Returns the number of rows written."""
    if not activities:
        return 0

    rows = [to_activity_row(payload, athlete_id) for payload in activities]

    # De-duplicate within the batch: ON CONFLICT can't touch the same row twice in
    # one statement, and Strava has been known to repeat an activity across pages.
    deduped: dict[int, dict[str, Any]] = {row["id"]: row for row in rows}

    statement = pg_insert(Activity).values(list(deduped.values()))
    statement = statement.on_conflict_do_update(
        index_elements=[Activity.id],
        set_={column: statement.excluded[column] for column in _UPDATABLE}
        | {"updated_at": statement.excluded["updated_at"]},
    )
    session.exec(statement)
    session.commit()
    return len(deduped)


def sync_athlete_activities(
    session: Session, athlete_id: int, after: datetime | None = None
) -> int:
    """Fetch and store this athlete's activities since `after` (default: backfill window)."""
    if after is None:
        after = datetime.now(UTC) - timedelta(days=get_settings().backfill_days)

    access_token = get_valid_access_token(session, athlete_id)
    activities = strava.fetch_activities(access_token, after)
    saved = save_activities_to_db(session, athlete_id, activities)
    logger.info("synced %s activities for athlete %s since %s", saved, athlete_id, after)
    return saved


def backfill_in_background(athlete_id: int) -> None:
    """Entry point for FastAPI BackgroundTasks — owns its own DB session.

    The request's session is already closed by the time this runs, and a failure here
    must never surface to the user mid-login, so everything is caught and logged.
    """
    try:
        with Session(engine) as session:
            saved = sync_athlete_activities(session, athlete_id)
        logger.info("backfill complete for athlete %s: %s activities", athlete_id, saved)
    except ReauthorizationRequired:
        logger.warning("backfill skipped for athlete %s: needs to reconnect Strava", athlete_id)
    except strava.StravaError as exc:
        logger.warning("backfill failed for athlete %s: %s", athlete_id, exc)
    except Exception:  # noqa: BLE001 - background task must not crash the worker
        logger.exception("unexpected backfill failure for athlete %s", athlete_id)
