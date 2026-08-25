"""Recap checkpoint: per-sport growth, trends, bests and consistency.

Run with:  .venv/bin/python -m scripts.check_recap
"""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session, delete

from app.config import get_settings
from app.infra.db import engine
from app.main import app
from app.models import Activity, Athlete
from app.services import recap
from app.services.session import create_session_token

ATHLETE_ID = 999_000_801
settings = get_settings()


def check(label: str, condition: bool, detail: str = "") -> None:
    assert condition, f"{label} FAILED {detail}"
    print(f"  ✓ {label}{(' — ' + detail) if detail else ''}")


def cleanup() -> None:
    with Session(engine) as session:
        session.exec(delete(Activity).where(Activity.owner_id == ATHLETE_ID))
        session.exec(delete(Athlete).where(Athlete.athlete_id == ATHLETE_ID))
        session.commit()


def activity(activity_id: int, days_ago: float, sport: str, km: float, minutes: float, hr: float | None = None, elevation: float = 0.0, suffer: int | None = None) -> Activity:
    raw = {"id": activity_id}
    if suffer is not None:
        raw["suffer_score"] = suffer
    return Activity(
        id=activity_id,
        owner_id=ATHLETE_ID,
        name=f"Activity {activity_id}",
        sport_type=sport,
        distance=km * 1000,
        moving_time=int(minutes * 60),
        elapsed_time=int(minutes * 60),
        total_elevation_gain=elevation,
        average_heartrate=hr,
        start_date=datetime.now(UTC) - timedelta(days=days_ago),
        raw_data=raw,
    )


def seed() -> None:
    cleanup()
    with Session(engine) as session:
        session.add(
            Athlete(
                athlete_id=ATHLETE_ID, name="Recap Tester",
                access_token="x", refresh_token="x",
                token_expires_at=datetime.now(UTC) + timedelta(hours=6),
            )
        )
        # Commit the athlete first: activities carry an FK to it.
        session.commit()

        # Older than both windows: establishes that history covers the comparison period,
        # which is what makes growth meaningful.
        session.add(activity(8000, 200, "Run", km=4, minutes=30, hr=172))
        # Same effort band as the current window's runs, so zone pace has a baseline to
        # improve against.
        session.add(activity(8010, 220, "Run", km=8, minutes=56, hr=158))
        session.add(activity(8011, 260, "Run", km=8, minutes=57, hr=157))
        # Previous 90-day window: two slow runs.
        session.add(activity(8001, 150, "Run", km=5, minutes=35, hr=170))
        session.add(activity(8002, 120, "Run", km=5, minutes=35, hr=170))
        # Current 90-day window: four faster runs, plus other sports.
        session.add(activity(8003, 60, "Run", km=10, minutes=60, hr=160, elevation=100, suffer=200))
        session.add(activity(8004, 40, "Run", km=10, minutes=58, hr=155))
        session.add(activity(8005, 20, "Run", km=12, minutes=66, hr=150, suffer=310))
        session.add(activity(8006, 5, "Run", km=5, minutes=25, hr=150))
        session.add(activity(8007, 10, "Tennis", km=0, minutes=90, hr=145))
        session.commit()


def main() -> None:
    seed()
    try:
        with Session(engine) as session:
            print("\noverview")
            data = recap.overview(session, ATHLETE_ID, days=90)
            check("window totals", data.total.activity_count == 5, str(data.total.activity_count))
            check("previous window counted separately", data.previous_total.activity_count == 2)
            check("baseline complete when history covers it", data.baseline_complete is True)

            sports = {s.sport_type: s for s in data.sports}
            check("sports split out", set(sports) == {"Run", "Tennis"})
            check("ordered by time invested",
                  [s.sport_type for s in data.sports][0] == "Run",
                  "runs total 209 min vs 90 for tennis")
            check("growth computed", sports["Run"].growth_activity_count == 100.0,
                  "4 runs vs 2 = +100%")
            check("no baseline for a new sport", sports["Tennis"].growth_distance is None)

            print("\nbaseline honesty")
            wide = recap.overview(session, ATHLETE_ID, days=365)
            check("incomplete baseline flagged", wide.baseline_complete is False,
                  "history starts inside the comparison window")
            check("growth suppressed when baseline is incomplete",
                  all(s.growth_activity_count is None for s in wide.sports))

            print("\nsport recap")
            run = recap.sport_recap(session, ATHLETE_ID, "Run", months=12)
            check("totals", run.totals.activity_count == 9)
            check("monthly points returned", len(run.months) >= 2, f"{len(run.months)} months")
            check("pace computed for a foot sport",
                  all(m.avg_pace_seconds_per_km is not None for m in run.months if m.distance > 100))
            check("speed left empty for a foot sport",
                  all(m.avg_speed_kmh is None for m in run.months))

            labels = {b.label: b for b in run.bests}
            check("longest distance", labels["Longest distance"].value == "12.0 km")
            check("fastest pace picks the quickest", labels["Fastest pace"].value == "5:00 /km",
                  "the 5 km in 25 min")
            check("most elevation", labels["Most elevation"].value == "100 m")
            check("hardest effort uses relative effort",
                  labels["Hardest effort"].value == "310 relative effort")

            check("consistency counts active weeks", run.consistency.active_weeks >= 4,
                  str(run.consistency.active_weeks))
            check("longest gap measured", run.consistency.longest_gap_days >= 20,
                  f"{run.consistency.longest_gap_days}d")

            print("\ntennis has no pace")
            tennis = recap.sport_recap(session, ATHLETE_ID, "Tennis", months=12)
            check("no pace for a court sport",
                  all(m.avg_pace_seconds_per_km is None for m in tennis.months))
            check("still reports time", tennis.totals.moving_time == 90 * 60)

            print("\nempty sport")
            empty = recap.sport_recap(session, ATHLETE_ID, "Swim", months=12)
            check("no activities", empty.totals.activity_count == 0)
            check("no bests", empty.bests == [])
            check("consistency degrades gracefully", empty.consistency.active_weeks == 0)

        print("\neffort zones")
        with Session(engine) as session:
            from app.services import zones as zones_service

            hr_max, basis = zones_service.estimate_hr_max(session, ATHLETE_ID)
            check("hr max estimated from history", hr_max > 0, f"{hr_max} bpm ({basis})")

            z = zones_service.zone_recap(session, ATHLETE_ID, "Run", months=6)
            by_zone = {bucket.zone: bucket for bucket in z.zones}
            check("runs bucketed by heart rate", len(by_zone) >= 2, str(sorted(by_zone)))
            check("every classified run lands in exactly one zone",
                  sum(b.activity_count for b in z.zones) == z.classified_count)
            check("zone bpm ranges derived from max",
                  all(b.low_bpm < b.high_bpm for b in z.zones))
            check("pace computed per zone",
                  all(b.avg_pace_seconds_per_km for b in z.zones if b.distance > 1000))
            check("monthly points carry a zone",
                  all(m.zone in by_zone for m in z.months))

            # The seeded runs get faster at a similar effort, so at least one zone should
            # show a negative (improving) delta against the previous period.
            deltas = [b.pace_delta_seconds for b in z.zones if b.pace_delta_seconds is not None]
            check("pace delta computed against the previous period", bool(deltas), str(deltas))

        print("\nzones without heart rate")
        with Session(engine) as session:
            session.exec(
                delete(Activity).where(Activity.owner_id == ATHLETE_ID, Activity.id == 8007)
            )
            session.add(activity(8100, 3, "Swim", km=1, minutes=30, hr=None))
            session.commit()
            z = zones_service.zone_recap(session, ATHLETE_ID, "Swim", months=6)
            check("unclassified counted", z.unclassified_count == 1)
            check("no zones invented", z.zones == [])

        print("\napi")
        client = TestClient(app)
        client.cookies.set(settings.session_cookie_name, create_session_token(ATHLETE_ID))
        r = client.get("/recap", params={"days": 90})
        check("overview 200", r.status_code == 200)
        r = client.get("/recap/Run", params={"months": 12})
        check("sport 200", r.status_code == 200 and r.json()["sport_type"] == "Run")
        r = client.get("/recap/Run/zones", params={"months": 12})
        check("zones 200", r.status_code == 200 and r.json()["hr_max"] > 0)
        check("days bounds enforced", client.get("/recap", params={"days": 1}).status_code == 422)

        anon = TestClient(app)
        check("anonymous → 401", anon.get("/recap").status_code == 401)
    finally:
        cleanup()

    print("\nRecap checks OK")


if __name__ == "__main__":
    main()
