"""Phase 6 checkpoint: activity fetch, upsert, and login-triggered backfill.

    .venv/bin/python -m scripts.check_activities          # stubbed, no network
    .venv/bin/python -m scripts.check_activities --live   # real fetch for the logged-in athlete

Run with:  .venv/bin/python -m scripts.check_activities
"""

import sys
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient
from sqlmodel import Session, delete, func, select

from app.config import get_settings
from app.infra import strava
from app.infra.db import engine
from app.main import app
from app.models import Activity, Athlete
from app.services import activities as activities_service
from app.services.session import create_session_token

FAKE_ATHLETE_ID = 999_000_201
settings = get_settings()


def check(label: str, condition: bool, detail: str = "") -> None:
    assert condition, f"{label} FAILED {detail}"
    print(f"  ✓ {label}{(' — ' + detail) if detail else ''}")


def _activity(activity_id: int, **overrides) -> dict:
    payload = {
        "id": activity_id,
        "name": "Morning Run",
        "sport_type": "Run",
        "distance": 5000.0,
        "moving_time": 1500,
        "elapsed_time": 1600,
        "total_elevation_gain": 42.0,
        "average_heartrate": 150.0,
        "max_heartrate": 170.0,
        "start_date": "2026-08-20T06:00:00Z",
    }
    payload.update(overrides)
    return payload


def cleanup() -> None:
    with Session(engine) as session:
        session.exec(delete(Activity).where(Activity.owner_id == FAKE_ATHLETE_ID))
        session.exec(delete(Athlete).where(Athlete.athlete_id == FAKE_ATHLETE_ID))
        session.commit()


def seed_athlete() -> None:
    cleanup()
    with Session(engine) as session:
        session.add(
            Athlete(
                athlete_id=FAKE_ATHLETE_ID,
                name="Sync Tester",
                access_token="fake-access",
                refresh_token="fake-refresh",
                token_expires_at=datetime.now(UTC) + timedelta(hours=6),
            )
        )
        session.commit()


def count_rows() -> int:
    with Session(engine) as session:
        return session.exec(
            select(func.count()).select_from(Activity).where(Activity.owner_id == FAKE_ATHLETE_ID)
        ).one()


def run_stubbed() -> None:
    seed_athlete()
    fetch_calls: list[tuple[str, datetime]] = []
    batch = [_activity(1001), _activity(1002, sport_type="Ride", distance=20000.0)]

    def fake_fetch(access_token: str, after: datetime) -> list[dict]:
        fetch_calls.append((access_token, after))
        return list(batch)

    original = strava.fetch_activities
    activities_service.strava.fetch_activities = fake_fetch
    try:
        print("\nfield mapping")
        row = activities_service.to_activity_row(
            _activity(1001, sport_type=None, type="Run"), FAKE_ATHLETE_ID
        )
        check("owner comes from the argument, not the payload", row["owner_id"] == FAKE_ATHLETE_ID)
        check("falls back to legacy `type`", row["sport_type"] == "Run")
        check("start_date parsed tz-aware", row["start_date"].tzinfo is not None)
        check("raw payload retained", row["raw_data"]["id"] == 1001)
        check("created_at == updated_at on first write", row["created_at"] == row["updated_at"])

        print("\nfirst sync")
        with Session(engine) as session:
            saved = activities_service.sync_athlete_activities(session, FAKE_ATHLETE_ID)
        check("saved both activities", saved == 2 and count_rows() == 2)
        check("used the default backfill window", fetch_calls[0][0] == "fake-access")
        window_days = (datetime.now(UTC) - fetch_calls[0][1]).days
        check(
            f"window is BACKFILL_DAYS ({settings.backfill_days}d)",
            window_days == settings.backfill_days,
            f"{window_days}d",
        )

        print("\nre-sync is an upsert, not a duplicate")
        batch[0] = _activity(1001, name="Renamed Run", distance=6000.0)
        with Session(engine) as session:
            activities_service.sync_athlete_activities(session, FAKE_ATHLETE_ID)
        check("row count unchanged", count_rows() == 2)
        with Session(engine) as session:
            stored = session.get(Activity, 1001)
            check("changed fields updated", stored.name == "Renamed Run" and stored.distance == 6000.0)
            check("updated_at bumped", stored.updated_at > stored.created_at)

        print("\nduplicate ids within one page")
        batch.append(_activity(1002, name="Duplicate"))
        with Session(engine) as session:
            saved = activities_service.sync_athlete_activities(session, FAKE_ATHLETE_ID)
        check("deduped before insert", saved == 2 and count_rows() == 2)
        batch.pop()

        print("\nempty result")
        batch.clear()
        with Session(engine) as session:
            saved = activities_service.sync_athlete_activities(session, FAKE_ATHLETE_ID)
        check("no-op, existing rows kept", saved == 0 and count_rows() == 2)

        print("\nbackfill triggered by login")
        cleanup()
        batch.extend([_activity(2001), _activity(2002)])

        def fake_exchange(code: str) -> dict:
            return {
                "access_token": "fake-access",
                "refresh_token": "fake-refresh",
                "expires_at": int((datetime.now(UTC) + timedelta(hours=6)).timestamp()),
                "athlete": {"id": FAKE_ATHLETE_ID, "firstname": "Sync", "lastname": "Tester"},
            }

        from app.services import auth as auth_service

        original_exchange = strava.exchange_code_for_tokens
        auth_service.strava.exchange_code_for_tokens = fake_exchange
        try:
            with TestClient(app, follow_redirects=False) as client:
                r = client.get("/auth/strava/login")
                state = parse_qs(urlparse(r.headers["location"]).query)["state"][0]
                r = client.get(
                    "/auth/strava/callback",
                    params={"code": "good", "state": state, "scope": "read,activity:read_all"},
                )
                check("login succeeded", r.status_code == 303)
            # TestClient runs background tasks before the context manager exits.
            check("backfill ran on login", count_rows() == 2, f"{count_rows()} rows")
        finally:
            auth_service.strava.exchange_code_for_tokens = original_exchange

        print("\nbackfill failure doesn't break login")
        cleanup()

        def exploding_fetch(access_token: str, after: datetime):
            raise strava.StravaError("boom")

        activities_service.strava.fetch_activities = exploding_fetch
        auth_service.strava.exchange_code_for_tokens = fake_exchange
        try:
            with TestClient(app, follow_redirects=False) as client:
                r = client.get("/auth/strava/login")
                state = parse_qs(urlparse(r.headers["location"]).query)["state"][0]
                r = client.get(
                    "/auth/strava/callback",
                    params={"code": "good", "state": state, "scope": "read,activity:read_all"},
                )
                check("login still succeeds", r.status_code == 303 and "login=ok" in r.headers["location"])
                r = client.get("/me")
                check("session still valid", r.status_code == 200)
        finally:
            auth_service.strava.exchange_code_for_tokens = original_exchange
            activities_service.strava.fetch_activities = fake_fetch

        print("\nsync endpoint requires auth")
        with TestClient(app) as client:
            check("anonymous → 401", client.post("/activities/sync").status_code == 401)
            client.cookies.set(settings.session_cookie_name, create_session_token(FAKE_ATHLETE_ID))
            batch.clear()
            batch.extend([_activity(3001)])
            r = client.post("/activities/sync", params={"days": 3})
            check("authenticated → 200", r.status_code == 200, str(r.json()))
            check("honours ?days", (datetime.now(UTC) - datetime.fromisoformat(r.json()["since"])).days == 3)
            r = client.post("/activities/sync", params={"days": 0})
            check("rejects days=0", r.status_code == 422)
    finally:
        activities_service.strava.fetch_activities = original
        cleanup()

    print("\nStubbed activity checks OK")


def run_live() -> None:
    with Session(engine) as session:
        athlete = session.exec(select(Athlete).where(Athlete.athlete_id < 999_000_000)).first()
        if athlete is None:
            print("no real athlete — log in first")
            sys.exit(1)
        athlete_id, name = athlete.athlete_id, athlete.name

    print(f"\nlive sync for athlete {athlete_id} ({name})")
    with Session(engine) as session:
        saved = activities_service.sync_athlete_activities(session, athlete_id)
    print(f"  fetched and stored {saved} activities from the last {settings.backfill_days} days")

    with Session(engine) as session:
        rows = session.exec(
            select(Activity).where(Activity.owner_id == athlete_id).order_by(Activity.start_date)
        ).all()
        for a in rows:
            km = (a.distance or 0) / 1000
            print(f"  {a.start_date:%Y-%m-%d %H:%M}  {a.sport_type:<15} {km:6.2f} km  {a.moving_time}s")
        check("activities stored", len(rows) > 0)
        oldest_allowed = datetime.now(UTC) - timedelta(days=settings.backfill_days + 1)
        check("all within the backfill window", all(a.start_date >= oldest_allowed for a in rows))
        check("raw payload kept for every row", all(a.raw_data for a in rows))
        check("every row belongs to this athlete", all(a.owner_id == athlete_id for a in rows))

    print("\nLive sync OK")


if __name__ == "__main__":
    run_stubbed()
    if "--live" in sys.argv:
        run_live()
