"""Strava webhook event handling.

Events arrive app-wide: every athlete who authorized the app, regardless of group.
Handlers are deliberately forgiving — Strava retries little, and a raised exception
in a background task helps nobody.
"""

import logging

from sqlmodel import Session, delete

from app.infra import strava
from app.infra.db import engine
from app.models import Activity, Athlete
from app.services.activities import save_activities_to_db
from app.services.errors import ReauthorizationRequired
from app.services.notifications import announce_activity
from app.services.push import notify_activity
from app.services.tokens import get_valid_access_token

logger = logging.getLogger(__name__)


def _handle_activity_upsert(session: Session, owner_id: int, activity_id: int) -> None:
    access_token = get_valid_access_token(session, owner_id)
    payload = strava.fetch_activity(access_token, activity_id)
    save_activities_to_db(session, owner_id, [payload])
    logger.info("webhook: stored activity %s for athlete %s", activity_id, owner_id)

    # Announce after storing, and never let a notification failure lose the activity.
    # The two channels are independent: Telegram going down must not cost anyone their
    # phone notification, or the other way round.
    try:
        announce_activity(session, activity_id)
    except Exception:  # noqa: BLE001
        logger.exception("webhook: announcing activity %s failed", activity_id)

    try:
        delivered = notify_activity(session, activity_id)
        logger.info("webhook: pushed activity %s to %s device(s)", activity_id, delivered)
    except Exception:  # noqa: BLE001
        logger.exception("webhook: pushing activity %s failed", activity_id)


def _handle_activity_delete(session: Session, owner_id: int, activity_id: int) -> None:
    session.exec(
        delete(Activity).where(Activity.id == activity_id, Activity.owner_id == owner_id)
    )
    session.commit()
    logger.info("webhook: deleted activity %s for athlete %s", activity_id, owner_id)


def _handle_deauthorization(session: Session, athlete_id: int) -> None:
    """The athlete revoked access, so remove their data.

    Deleting the Athlete row cascades to their activities and group memberships. Groups
    they created survive (created_by is ON DELETE SET NULL).
    """
    athlete = session.get(Athlete, athlete_id)
    if athlete is None:
        return
    session.delete(athlete)
    session.commit()
    logger.info("webhook: athlete %s deauthorized, data removed", athlete_id)


def process_event(
    object_type: str,
    object_id: int,
    aspect_type: str,
    owner_id: int,
    updates: dict | None = None,
) -> None:
    """Apply one webhook event. Runs as a background task with its own session."""
    updates = updates or {}
    try:
        with Session(engine) as session:
            # Ignore events for athletes who never authorized *this* deployment —
            # the local and production apps share one Strava app, so both receive
            # every event.
            if session.get(Athlete, owner_id) is None:
                logger.info("webhook: ignoring event for unknown athlete %s", owner_id)
                return

            if object_type == "athlete":
                if str(updates.get("authorized", "")).lower() == "false":
                    _handle_deauthorization(session, owner_id)
                return

            if object_type != "activity":
                logger.info("webhook: ignoring object_type %r", object_type)
                return

            if aspect_type in ("create", "update"):
                _handle_activity_upsert(session, owner_id, object_id)
            elif aspect_type == "delete":
                _handle_activity_delete(session, owner_id, object_id)
            else:
                logger.info("webhook: ignoring aspect_type %r", aspect_type)
    except ReauthorizationRequired:
        logger.warning("webhook: athlete %s needs to reconnect Strava", owner_id)
    except strava.StravaError as exc:
        logger.warning("webhook: Strava call failed for athlete %s: %s", owner_id, exc)
    except Exception:  # noqa: BLE001 - a background task must never crash the worker
        logger.exception("webhook: unexpected failure handling event for athlete %s", owner_id)
