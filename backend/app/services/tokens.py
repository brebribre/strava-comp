"""Access token lifecycle.

Strava access tokens last ~6 hours. Everything that calls the Strava API on an
athlete's behalf goes through get_valid_access_token, so expiry is handled in one
place rather than at each call site.
"""

from datetime import UTC, datetime, timedelta

from sqlmodel import Session, select

from app.infra import strava
from app.models import Athlete
from app.services.errors import AthleteNotFound, ReauthorizationRequired

# Refresh slightly early, so a token can't expire between this check and the API call.
EXPIRY_SKEW = timedelta(minutes=5)


def is_expired(athlete: Athlete, now: datetime | None = None) -> bool:
    now = now or datetime.now(UTC)
    return athlete.token_expires_at <= now + EXPIRY_SKEW


def get_valid_access_token(session: Session, athlete_id: int) -> str:
    """Return a usable access token, refreshing it via Strava first if needed.

    The athlete row is locked FOR UPDATE for the duration. Phase 7's webhook bursts
    can hit the same athlete concurrently; without the lock, parallel refreshes race
    and one of them writes a stale token back over the fresh one.
    """
    athlete = session.exec(
        select(Athlete).where(Athlete.athlete_id == athlete_id).with_for_update()
    ).first()
    if athlete is None:
        session.rollback()
        raise AthleteNotFound(f"no athlete {athlete_id}")

    if not is_expired(athlete):
        token = athlete.access_token
        session.commit()  # release the row lock
        return token

    try:
        payload = strava.refresh_access_token(athlete.refresh_token)
    except strava.StravaError as exc:
        session.rollback()
        # A rejected refresh token means the athlete revoked access (or it was
        # rotated away); no amount of retrying fixes it, they have to reconnect.
        raise ReauthorizationRequired(f"refresh failed for athlete {athlete_id}: {exc}") from exc

    athlete.access_token = payload["access_token"]
    # Strava can hand back a new refresh token — persisting it is not optional.
    athlete.refresh_token = payload["refresh_token"]
    athlete.token_expires_at = datetime.fromtimestamp(int(payload["expires_at"]), tz=UTC)
    session.add(athlete)
    session.commit()
    session.refresh(athlete)
    return athlete.access_token
