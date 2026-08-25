"""Target checkpoint: qualification rules, period maths, and progress.

Run with:  .venv/bin/python -m scripts.check_target
"""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session, delete, select

from app.config import get_settings
from app.infra.db import engine
from app.main import app
from app.models import Activity, Athlete, Group, GroupMembership, GroupTarget
from app.schemas.target import TargetRules
from app.services.session import create_session_token
from app.services.target import period_bounds, qualifies

ALICE_ID = 999_000_501
BOB_ID = 999_000_502
CAROL_ID = 999_000_503
SEEDED = (ALICE_ID, BOB_ID, CAROL_ID)

settings = get_settings()


def check(label: str, condition: bool, detail: str = "") -> None:
    assert condition, f"{label} FAILED {detail}"
    print(f"  ✓ {label}{(' — ' + detail) if detail else ''}")


def cleanup() -> None:
    with Session(engine) as session:
        ids = [g.id for g in session.exec(select(Group).where(Group.created_by.in_(SEEDED))).all()]
        if ids:
            session.exec(delete(GroupTarget).where(GroupTarget.group_id.in_(ids)))
            session.exec(delete(GroupMembership).where(GroupMembership.group_id.in_(ids)))
            session.exec(delete(Group).where(Group.id.in_(ids)))
        session.exec(delete(Activity).where(Activity.owner_id.in_(SEEDED)))
        session.exec(delete(GroupMembership).where(GroupMembership.athlete_id.in_(SEEDED)))
        session.exec(delete(Athlete).where(Athlete.athlete_id.in_(SEEDED)))
        session.commit()


def activity(activity_id: int, owner_id: int, when: datetime, sport: str, minutes: float, km: float = 0.0) -> Activity:
    return Activity(
        id=activity_id,
        owner_id=owner_id,
        name=f"Activity {activity_id}",
        sport_type=sport,
        distance=km * 1000,
        moving_time=int(minutes * 60),
        elapsed_time=int(minutes * 60),
        total_elevation_gain=0.0,
        start_date=when,
        raw_data={"id": activity_id},
    )


def seed() -> int:
    cleanup()
    now = datetime.now(UTC)
    this_week_start, _ = period_bounds("week", now)
    # Midday on the first day of this week — safely inside the period regardless of "now".
    inside = this_week_start + timedelta(hours=12)
    last_week = this_week_start - timedelta(days=2)

    with Session(engine) as session:
        for athlete_id, name in ((ALICE_ID, "Alice"), (BOB_ID, "Bob"), (CAROL_ID, "Carol")):
            session.add(
                Athlete(
                    athlete_id=athlete_id,
                    name=name,
                    access_token="x",
                    refresh_token="x",
                    token_expires_at=now + timedelta(hours=6),
                )
            )
        group = Group(name="Target Test", invite_code="target-test-1", created_by=ALICE_ID)
        session.add(group)
        session.commit()
        session.refresh(group)

        session.add(GroupMembership(group_id=group.id, athlete_id=ALICE_ID))
        session.add(GroupMembership(group_id=group.id, athlete_id=BOB_ID))

        # Alice, this period: 3 qualify, 2 don't.
        session.add(activity(5001, ALICE_ID, inside, "Run", minutes=25, km=4))       # time + distance
        session.add(activity(5002, ALICE_ID, inside, "Run", minutes=12, km=3.5))     # distance only
        session.add(activity(5003, ALICE_ID, inside, "Tennis", minutes=60))          # time
        session.add(activity(5004, ALICE_ID, inside, "Run", minutes=10, km=1))       # too short and too near
        session.add(activity(5005, ALICE_ID, inside, "Yoga", minutes=15))            # under the default
        # Outside the current period — must not count.
        session.add(activity(5006, ALICE_ID, last_week, "Tennis", minutes=90))
        # Bob does nothing. Carol isn't a member but trains hard.
        session.add(activity(5007, CAROL_ID, inside, "Run", minutes=90, km=15))
        session.commit()
        return group.id


def main() -> None:
    group_id = seed()
    try:
        rules = TargetRules.model_validate(
            {
                "default_min_minutes": 30,
                "sports": {
                    "Run": {"min_minutes": 20, "min_distance_km": 3},
                    "Tennis": {"min_minutes": 45},
                    "WeightTraining": {"min_minutes": 30},
                },
            }
        )
        now = datetime.now(UTC)

        print("\nqualification rules")
        check("run qualifies on time", qualifies(activity(1, 1, now, "Run", 25, 1), rules))
        check("run qualifies on distance alone", qualifies(activity(1, 1, now, "Run", 12, 3.5), rules),
              "short but far — time OR distance")
        check("run failing both is rejected", not qualifies(activity(1, 1, now, "Run", 10, 1), rules))
        check("tennis qualifies on time", qualifies(activity(1, 1, now, "Tennis", 60), rules))
        check("short tennis rejected", not qualifies(activity(1, 1, now, "Tennis", 30), rules))
        check("long tennis distance is irrelevant",
              not qualifies(activity(1, 1, now, "Tennis", 30, 99), rules),
              "no distance rule for tennis")
        check("weights qualify on time", qualifies(activity(1, 1, now, "WeightTraining", 45), rules))
        check("undefined sport uses the default", qualifies(activity(1, 1, now, "Yoga", 35), rules))
        check("undefined sport under the default is rejected",
              not qualifies(activity(1, 1, now, "Yoga", 15), rules))
        check("missing sport_type uses the default", qualifies(activity(1, 1, now, None, 45), rules))
        check("exactly at the threshold counts", qualifies(activity(1, 1, now, "Run", 20, 0), rules))

        print("\nperiod boundaries")
        wednesday = datetime(2026, 8, 19, 15, 0, tzinfo=UTC)
        start, end = period_bounds("week", wednesday)
        check("week starts Monday", start == datetime(2026, 8, 17, tzinfo=UTC), str(start))
        check("week is 7 days", (end - start).days == 7)
        start, end = period_bounds("month", wednesday)
        check("month starts on the 1st", start == datetime(2026, 8, 1, tzinfo=UTC))
        check("august has 31 days", (end - start).days == 31)
        start, end = period_bounds("year", wednesday)
        check("year starts Jan 1", start == datetime(2026, 1, 1, tzinfo=UTC))
        check("year ends next Jan 1", end == datetime(2027, 1, 1, tzinfo=UTC))
        # A February in a leap year is the classic off-by-one.
        start, end = period_bounds("month", datetime(2028, 2, 10, tzinfo=UTC))
        check("leap February has 29 days", (end - start).days == 29)
        # December must roll into the next year, not month 13.
        start, end = period_bounds("month", datetime(2026, 12, 15, tzinfo=UTC))
        check("december rolls into January", end == datetime(2027, 1, 1, tzinfo=UTC), str(end))

        print("\napi: no target yet")
        alice = TestClient(app)
        alice.cookies.set(settings.session_cookie_name, create_session_token(ALICE_ID))
        carol = TestClient(app)
        carol.cookies.set(settings.session_cookie_name, create_session_token(CAROL_ID))
        anon = TestClient(app)

        check("GET target → 404", alice.get(f"/groups/{group_id}/target").status_code == 404)
        check("GET progress → 404", alice.get(f"/groups/{group_id}/target/progress").status_code == 404)

        print("\napi: set a target")
        payload = {
            "count": 4,
            "period": "week",
            "until": (now + timedelta(days=90)).isoformat(),
            "rules": rules.model_dump(mode="json"),
        }
        r = alice.put(f"/groups/{group_id}/target", json=payload)
        check("PUT → 200", r.status_code == 200, str(r.json())[:200])
        check("rules round-trip", r.json()["rules"]["sports"]["Run"]["min_distance_km"] == 3)

        r = alice.put(f"/groups/{group_id}/target", json={**payload, "count": 5})
        check("PUT again replaces rather than duplicating", r.status_code == 200 and r.json()["count"] == 5)
        with Session(engine) as session:
            count = len(session.exec(select(GroupTarget).where(GroupTarget.group_id == group_id)).all())
        check("still exactly one target row", count == 1)

        check("count=0 rejected", alice.put(f"/groups/{group_id}/target", json={**payload, "count": 0}).status_code == 422)
        check("unknown period rejected", alice.put(f"/groups/{group_id}/target", json={**payload, "period": "fortnight"}).status_code == 422)

        alice.put(f"/groups/{group_id}/target", json=payload)  # back to 4

        print("\napi: progress")
        r = alice.get(f"/groups/{group_id}/target/progress")
        check("200", r.status_code == 200)
        data = r.json()
        members = {m["athlete_id"]: m for m in data["members"]}
        check("only members listed", set(members) == {ALICE_ID, BOB_ID})
        check("alice counted 3 qualifying", members[ALICE_ID]["completed"] == 3, str(members[ALICE_ID]))
        check("non-qualifying and older activities excluded", members[ALICE_ID]["completed"] != 6)
        check("remaining computed", members[ALICE_ID]["remaining"] == 1)
        check("percent computed", members[ALICE_ID]["percent"] == 75.0)
        check("not yet complete", members[ALICE_ID]["is_complete"] is False)
        check("inactive member at zero", members[BOB_ID]["completed"] == 0 and members[BOB_ID]["remaining"] == 4)
        check("ordered furthest ahead first",
              [m["athlete_id"] for m in data["members"]] == [ALICE_ID, BOB_ID])
        check("period is the current week", data["period_start"][:10] == period_bounds("week", now)[0].date().isoformat())
        check("not expired", data["is_expired"] is False)
        check("periods remaining counted", data["periods_remaining"] >= 12, str(data["periods_remaining"]))

        print("\napi: over-achievement clamps")
        alice.put(f"/groups/{group_id}/target", json={**payload, "count": 2})
        r = alice.get(f"/groups/{group_id}/target/progress")
        me = {m["athlete_id"]: m for m in r.json()["members"]}[ALICE_ID]
        check("completed can exceed the target", me["completed"] == 3)
        check("remaining floors at zero", me["remaining"] == 0)
        check("percent caps at 100", me["percent"] == 100.0)
        check("marked complete", me["is_complete"] is True)

        print("\napi: expiry")
        alice.put(f"/groups/{group_id}/target", json={**payload, "until": (now - timedelta(days=1)).isoformat()})
        r = alice.get(f"/groups/{group_id}/target/progress")
        check("past `until` is flagged expired", r.json()["is_expired"] is True)
        check("expired target reports no periods remaining", r.json()["periods_remaining"] == 0)

        print("\napi: start date")
        alice.put(f"/groups/{group_id}/target", json=payload)
        r = alice.get(f"/groups/{group_id}/target")
        started = datetime.fromisoformat(r.json()["starts_at"])
        check("an omitted start date defaults to the start of the period",
              started == period_bounds("week", datetime.now(UTC))[0], str(started))
        check("so activities earlier in the period still count",
              {m["athlete_id"]: m for m in
               alice.get(f"/groups/{group_id}/target/progress").json()["members"]
               }[ALICE_ID]["completed"] == 3)

        check("until before starts_at rejected",
              alice.put(
                  f"/groups/{group_id}/target",
                  json={**payload, "starts_at": (now + timedelta(days=100)).isoformat()},
              ).status_code == 422,
              "until is only 90 days out")

        week_start = period_bounds("week", now)[0]
        # Every seeded activity sits at Monday noon; starting after that must discount them
        # even though they are inside the current period.
        alice.put(
            f"/groups/{group_id}/target",
            json={**payload, "starts_at": (week_start + timedelta(hours=12, minutes=1)).isoformat()},
        )
        r = alice.get(f"/groups/{group_id}/target/progress")
        by_id = {m["athlete_id"]: m for m in r.json()["members"]}
        check("activities before the start date do not count", by_id[ALICE_ID]["completed"] == 0,
              "same period, but earlier than starts_at")

        alice.put(f"/groups/{group_id}/target", json={**payload, "starts_at": week_start.isoformat()})
        r = alice.get(f"/groups/{group_id}/target/progress")
        by_id = {m["athlete_id"]: m for m in r.json()["members"]}
        check("starting at the period start counts them again", by_id[ALICE_ID]["completed"] == 3)
        check("a started target is not pending", r.json()["is_pending"] is False)

        alice.put(
            f"/groups/{group_id}/target",
            json={**payload, "starts_at": (now + timedelta(days=2)).isoformat()},
        )
        r = alice.get(f"/groups/{group_id}/target/progress")
        check("a future start date is flagged pending", r.json()["is_pending"] is True)
        check("a pending target counts nothing yet",
              all(m["completed"] == 0 for m in r.json()["members"]))

        alice.put(
            f"/groups/{group_id}/target",
            json={**payload, "starts_at": (week_start - timedelta(weeks=2)).isoformat()},
        )
        h = alice.get(f"/groups/{group_id}/target/history", params={"weeks": 6}).json()
        check("weeks inside the window are in scope", h["weeks"][0]["in_scope"] is True)
        check("weeks before the start date are out of scope", h["weeks"][5]["in_scope"] is False,
              "not failures — the target did not exist yet")
        check("exactly the covered weeks are in scope",
              sum(1 for w in h["weeks"] if w["in_scope"]) == 3, "started two weeks ago")

        alice.put(f"/groups/{group_id}/target", json=payload)

        print("\nweekly history")
        r = alice.get(f"/groups/{group_id}/target/history", params={"weeks": 6})
        check("200", r.status_code == 200, str(r.json())[:150])
        history = r.json()
        check("newest week first", history["weeks"][0]["is_current"] is True)
        check("requested number of weeks", len(history["weeks"]) == 6)
        check("every member present in each week",
              all({m["athlete_id"] for m in w["members"]} == {ALICE_ID, BOB_ID} for w in history["weeks"]))

        this_week = history["weeks"][0]
        mine = next(m for m in this_week["members"] if m["athlete_id"] == ALICE_ID)
        check("current week counts qualifying activities", mine["completed"] == 3, str(mine))
        check("inactive member at zero",
              next(m for m in this_week["members"] if m["athlete_id"] == BOB_ID)["completed"] == 0)
        check("older week counted separately",
              all(m["completed"] == 0 for m in history["weeks"][2]["members"]))

        r = alice.put(f"/groups/{group_id}/target", json={**payload, "count": 8, "period": "month"})
        r = alice.get(f"/groups/{group_id}/target/history", params={"weeks": 4})
        check("a monthly target is spread across weeks", r.json()["target_count"] == 2,
              "8 per month ≈ 2 per week")
        alice.put(f"/groups/{group_id}/target", json=payload)

        print("\napi: access control")
        check("non-member GET → 403", carol.get(f"/groups/{group_id}/target").status_code == 403)
        check("non-member PUT → 403", carol.put(f"/groups/{group_id}/target", json=payload).status_code == 403)
        check("non-member progress → 403", carol.get(f"/groups/{group_id}/target/progress").status_code == 403)
        check("anonymous → 401", anon.get(f"/groups/{group_id}/target").status_code == 401)
        check("non-member history → 403",
              carol.get(f"/groups/{group_id}/target/history").status_code == 403)

        print("\napi: delete")
        check("DELETE → 204", alice.delete(f"/groups/{group_id}/target").status_code == 204)
        check("GET after delete → 404", alice.get(f"/groups/{group_id}/target").status_code == 404)
        check("second DELETE → 404", alice.delete(f"/groups/{group_id}/target").status_code == 404)
    finally:
        cleanup()

    print("\nTarget checks OK")


if __name__ == "__main__":
    main()
