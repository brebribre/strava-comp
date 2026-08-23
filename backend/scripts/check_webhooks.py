"""Phase 7 checkpoint: webhook verification and event handling.

Run with:  .venv/bin/python -m scripts.check_webhooks
"""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session, delete, select

from app.config import get_settings
from app.infra import strava
from app.infra.db import engine
from app.main import app
from app.models import Activity, Athlete
from app.services import webhooks as webhooks_service

FAKE_ATHLETE_ID = 999_000_301
UNKNOWN_ATHLETE_ID = 999_000_999
ACTIVITY_ID = 14_500_000_000_001

settings = get_settings()


def check(label: str, condition: bool, detail: str = "") -> None:
    assert condition, f"{label} FAILED {detail}"
    print(f"  ✓ {label}{(' — ' + detail) if detail else ''}")


def cleanup() -> None:
    with Session(engine) as session:
        session.exec(delete(Activity).where(Activity.owner_id.in_([FAKE_ATHLETE_ID, UNKNOWN_ATHLETE_ID])))
        session.exec(delete(Athlete).where(Athlete.athlete_id.in_([FAKE_ATHLETE_ID, UNKNOWN_ATHLETE_ID])))
        session.commit()


def seed() -> None:
    cleanup()
    with Session(engine) as session:
        session.add(
            Athlete(
                athlete_id=FAKE_ATHLETE_ID,
                name="Webhook Tester",
                access_token="fake-access",
                refresh_token="fake-refresh",
                token_expires_at=datetime.now(UTC) + timedelta(hours=6),
            )
        )
        session.commit()


def activity_count(owner_id: int = FAKE_ATHLETE_ID) -> int:
    with Session(engine) as session:
        return len(session.exec(select(Activity).where(Activity.owner_id == owner_id)).all())


def event(**overrides) -> dict:
    payload = {
        "object_type": "activity",
        "object_id": ACTIVITY_ID,
        "aspect_type": "create",
        "owner_id": FAKE_ATHLETE_ID,
        "subscription_id": 12345,
        "event_time": int(datetime.now(UTC).timestamp()),
    }
    payload.update(overrides)
    return payload


def main() -> None:
    seed()
    fetched: list[int] = []

    def fake_fetch_activity(access_token: str, activity_id: int) -> dict:
        fetched.append(activity_id)
        return {
            "id": activity_id,
            "name": "Webhook Run",
            "sport_type": "Run",
            "distance": 7000.0,
            "moving_time": 2000,
            "elapsed_time": 2100,
            "total_elevation_gain": 30.0,
            "average_heartrate": 152.0,
            "max_heartrate": 175.0,
            "start_date": "2026-08-23T07:00:00Z",
        }

    original = strava.fetch_activity
    webhooks_service.strava.fetch_activity = fake_fetch_activity
    try:
        with TestClient(app) as client:
            print("\nsubscription validation")
            r = client.get(
                "/strava/webhook",
                params={
                    "hub.mode": "subscribe",
                    "hub.challenge": "abc123",
                    "hub.verify_token": settings.strava_verify_token,
                },
            )
            check("echoes hub.challenge", r.status_code == 200 and r.json() == {"hub.challenge": "abc123"})
            r = client.get(
                "/strava/webhook",
                params={"hub.mode": "subscribe", "hub.challenge": "x", "hub.verify_token": "wrong"},
            )
            check("wrong verify_token → 403", r.status_code == 403)
            r = client.get(
                "/strava/webhook",
                params={"hub.mode": "unsubscribe", "hub.challenge": "x", "hub.verify_token": settings.strava_verify_token},
            )
            check("unexpected hub.mode → 400", r.status_code == 400)

            print("\nactivity create")
            r = client.post("/strava/webhook", json=event())
            check("acked with 200", r.status_code == 200, str(r.json()))
            check("activity fetched and stored", activity_count() == 1 and fetched == [ACTIVITY_ID])
            with Session(engine) as session:
                stored = session.get(Activity, ACTIVITY_ID)
                check("owner set from event", stored.owner_id == FAKE_ATHLETE_ID)
                check("raw payload kept", stored.raw_data["name"] == "Webhook Run")

            print("\nactivity update")
            fetched.clear()
            r = client.post("/strava/webhook", json=event(aspect_type="update", updates={"title": "Renamed"}))
            check("re-fetched, not duplicated", activity_count() == 1 and fetched == [ACTIVITY_ID])

            print("\nactivity delete")
            r = client.post("/strava/webhook", json=event(aspect_type="delete"))
            check("row removed", activity_count() == 0)

            print("\nunknown athlete")
            fetched.clear()
            r = client.post("/strava/webhook", json=event(owner_id=UNKNOWN_ATHLETE_ID))
            check("acked", r.status_code == 200)
            check("no Strava call made", fetched == [])
            check("nothing stored", activity_count(UNKNOWN_ATHLETE_ID) == 0)

            print("\nmalformed payloads")
            check("garbage acked", client.post("/strava/webhook", json={"nope": 1}).status_code == 200)
            check(
                "non-json acked",
                client.post("/strava/webhook", content=b"not json").status_code == 200,
            )

            print("\nunhandled event types")
            fetched.clear()
            r = client.post("/strava/webhook", json=event(object_type="segment"))
            check("unknown object_type ignored", r.status_code == 200 and fetched == [])

            print("\nStrava failure during handling")
            def exploding(access_token: str, activity_id: int) -> dict:
                raise strava.StravaError("boom")

            webhooks_service.strava.fetch_activity = exploding
            r = client.post("/strava/webhook", json=event())
            check("still acked with 200", r.status_code == 200)
            check("nothing stored", activity_count() == 0)
            webhooks_service.strava.fetch_activity = fake_fetch_activity

            print("\ndeauthorization")
            client.post("/strava/webhook", json=event())
            check("activity present before deauth", activity_count() == 1)
            r = client.post(
                "/strava/webhook",
                json=event(object_type="athlete", object_id=FAKE_ATHLETE_ID, aspect_type="update", updates={"authorized": "false"}),
            )
            check("acked", r.status_code == 200)
            with Session(engine) as session:
                check("athlete row removed", session.get(Athlete, FAKE_ATHLETE_ID) is None)
            check("activities cascaded away", activity_count() == 0)
    finally:
        webhooks_service.strava.fetch_activity = original
        cleanup()

    print("\nPhase 7 webhook checks OK")


if __name__ == "__main__":
    main()
