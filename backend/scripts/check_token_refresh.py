"""Phase 4 checkpoint: token refresh.

    .venv/bin/python -m scripts.check_token_refresh          # stubbed, no network
    .venv/bin/python -m scripts.check_token_refresh --live   # real refresh against Strava

--live back-dates the real athlete's token_expires_at, forces a refresh through
Strava, and confirms fresh credentials land in the DB.
"""

import sys
from datetime import UTC, datetime, timedelta

from sqlmodel import Session, delete, select

from app.infra import strava
from app.infra.db import engine
from app.models import Athlete
from app.services import tokens
from app.services.errors import AthleteNotFound, ReauthorizationRequired

FAKE_ATHLETE_ID = 999_000_077


def check(label: str, condition: bool, detail: str = "") -> None:
    assert condition, f"{label} FAILED {detail}"
    print(f"  ✓ {label}{(' — ' + detail) if detail else ''}")


def _cleanup() -> None:
    with Session(engine) as session:
        session.exec(delete(Athlete).where(Athlete.athlete_id == FAKE_ATHLETE_ID))
        session.commit()


def _seed(expires_in: timedelta) -> None:
    _cleanup()
    with Session(engine) as session:
        session.add(
            Athlete(
                athlete_id=FAKE_ATHLETE_ID,
                name="Refresh Test",
                access_token="old-access",
                refresh_token="old-refresh",
                token_expires_at=datetime.now(UTC) + expires_in,
            )
        )
        session.commit()


def run_stubbed() -> None:
    calls: list[str] = []

    def fake_refresh(refresh_token: str) -> dict:
        calls.append(refresh_token)
        if refresh_token == "revoked-refresh":
            raise strava.StravaError("token refresh failed (400)")
        return {
            "access_token": "new-access",
            "refresh_token": "new-refresh",  # Strava may rotate it
            "expires_at": int((datetime.now(UTC) + timedelta(hours=6)).timestamp()),
        }

    original = strava.refresh_access_token
    tokens.strava.refresh_access_token = fake_refresh
    try:
        print("\nvalid token")
        _seed(timedelta(hours=5))
        with Session(engine) as session:
            token = tokens.get_valid_access_token(session, FAKE_ATHLETE_ID)
        check("returns stored token", token == "old-access")
        check("no call to Strava", calls == [], f"calls={calls}")

        print("\nexpired token")
        _seed(timedelta(hours=-1))
        with Session(engine) as session:
            token = tokens.get_valid_access_token(session, FAKE_ATHLETE_ID)
        check("returns refreshed token", token == "new-access")
        check("called Strava with stored refresh token", calls == ["old-refresh"], f"calls={calls}")
        with Session(engine) as session:
            stored = session.get(Athlete, FAKE_ATHLETE_ID)
            check("access token persisted", stored.access_token == "new-access")
            check("rotated refresh token persisted", stored.refresh_token == "new-refresh")
            check("expiry moved into the future", stored.token_expires_at > datetime.now(UTC))

        print("\nabout to expire (within the 5-minute skew)")
        calls.clear()
        _seed(timedelta(minutes=2))
        with Session(engine) as session:
            token = tokens.get_valid_access_token(session, FAKE_ATHLETE_ID)
        check("refreshed pre-emptively", token == "new-access" and calls == ["old-refresh"])

        print("\nrevoked refresh token")
        calls.clear()
        _cleanup()
        with Session(engine) as session:
            session.add(
                Athlete(
                    athlete_id=FAKE_ATHLETE_ID,
                    name="Revoked",
                    access_token="old-access",
                    refresh_token="revoked-refresh",
                    token_expires_at=datetime.now(UTC) - timedelta(hours=1),
                )
            )
            session.commit()
        with Session(engine) as session:
            try:
                tokens.get_valid_access_token(session, FAKE_ATHLETE_ID)
                raise AssertionError("should have raised ReauthorizationRequired")
            except ReauthorizationRequired:
                pass
        check("raises ReauthorizationRequired", True)
        with Session(engine) as session:
            stored = session.get(Athlete, FAKE_ATHLETE_ID)
            check("stored tokens left untouched", stored.access_token == "old-access")

        print("\nunknown athlete")
        with Session(engine) as session:
            try:
                tokens.get_valid_access_token(session, 1)
                raise AssertionError("should have raised AthleteNotFound")
            except AthleteNotFound:
                pass
        check("raises AthleteNotFound", True)
    finally:
        tokens.strava.refresh_access_token = original
        _cleanup()

    print("\nStubbed refresh checks OK")


def run_live() -> None:
    """Force a real refresh against Strava for the logged-in athlete.

    Note: while the current access token is still valid, Strava's refresh endpoint
    returns that same token and expiry rather than minting a new one. So the proof
    that a refresh really happened is (a) we counted the outbound call, and (b) the
    expiry we had deliberately back-dated came back correct from Strava's response.
    """
    import httpx

    with Session(engine) as session:
        athlete = session.exec(
            select(Athlete).where(Athlete.athlete_id != FAKE_ATHLETE_ID)
        ).first()
        if athlete is None:
            print("no real athlete in the DB — log in first")
            sys.exit(1)
        athlete_id = athlete.athlete_id
        print(f"\nlive refresh for athlete {athlete_id} ({athlete.name})")
        print(f"  token_expires_at as stored  : {athlete.token_expires_at}")

        # Back-date the expiry so the next call is forced to go out to Strava.
        athlete.token_expires_at = datetime.now(UTC) - timedelta(minutes=1)
        session.add(athlete)
        session.commit()
        print(f"  token_expires_at back-dated : {athlete.token_expires_at}")

    calls: list[str] = []
    real_refresh = strava.refresh_access_token

    def counting_refresh(refresh_token: str) -> dict:
        calls.append(refresh_token)
        return real_refresh(refresh_token)

    tokens.strava.refresh_access_token = counting_refresh
    try:
        with Session(engine) as session:
            token = tokens.get_valid_access_token(session, athlete_id)
    finally:
        tokens.strava.refresh_access_token = real_refresh

    with Session(engine) as session:
        after = session.get(Athlete, athlete_id)
        print(f"  token_expires_at after      : {after.token_expires_at}")
        check("Strava was actually called", len(calls) == 1)
        check("expiry restored to the future", after.token_expires_at > datetime.now(UTC))
        check("returned token matches stored", token == after.access_token)
        check("refresh token still present", bool(after.refresh_token))

    # Does the refreshed token actually work against the data API?
    response = httpx.get(
        f"{strava.STRAVA_API_BASE}/athlete",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10.0,
    )
    if response.status_code == 403 and "Inactive" in response.text:
        # Not a token problem: Strava's Developer Program Standard Tier requires the
        # app owner to hold a paid Strava subscription, otherwise every data-API call
        # is refused while OAuth and token refresh keep working. Phases 6-8 are blocked
        # until the app is reactivated at strava.com/settings/api.
        print("  ! data API refused: app is INACTIVE (owner needs a paid Strava subscription)")
        print(f"    {response.text}")
    else:
        check("token authenticates against Strava", response.status_code == 200, f"HTTP {response.status_code}")
        check("Strava reports the same athlete", response.json().get("id") == athlete_id)

    print("\nLive refresh OK")


if __name__ == "__main__":
    run_stubbed()
    if "--live" in sys.argv:
        run_live()
