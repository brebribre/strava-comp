"""Login logic: turn a Strava authorization code into a stored athlete."""

from datetime import UTC, datetime
from typing import Any

from sqlmodel import Session

from app.infra import strava
from app.models import Athlete


def _athlete_name(athlete_payload: dict[str, Any], athlete_id: int) -> str:
    first = (athlete_payload.get("firstname") or "").strip()
    last = (athlete_payload.get("lastname") or "").strip()
    return " ".join(part for part in (first, last) if part) or f"Athlete {athlete_id}"


def upsert_athlete_from_token_payload(session: Session, payload: dict[str, Any]) -> Athlete:
    """Create or update the Athlete row from Strava's token response."""
    athlete_payload = payload["athlete"]
    athlete_id = int(athlete_payload["id"])
    expires_at = datetime.fromtimestamp(int(payload["expires_at"]), tz=UTC)

    athlete = session.get(Athlete, athlete_id)
    if athlete is None:
        athlete = Athlete(
            athlete_id=athlete_id,
            name=_athlete_name(athlete_payload, athlete_id),
            access_token=payload["access_token"],
            refresh_token=payload["refresh_token"],
            token_expires_at=expires_at,
        )
        session.add(athlete)
    else:
        # Returning user: refresh the stored credentials and display name.
        athlete.name = _athlete_name(athlete_payload, athlete_id)
        athlete.access_token = payload["access_token"]
        athlete.refresh_token = payload["refresh_token"]
        athlete.token_expires_at = expires_at
        session.add(athlete)

    session.commit()
    session.refresh(athlete)
    return athlete


def login_with_code(session: Session, code: str) -> Athlete:
    """Exchange the OAuth code and persist the athlete. Raises StravaError on failure."""
    payload = strava.exchange_code_for_tokens(code)
    return upsert_athlete_from_token_payload(session, payload)
