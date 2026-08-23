"""Phase 8 checkpoint: group summary and trend endpoints.

Run with:  .venv/bin/python -m scripts.check_summary
"""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session, delete, select

from app.config import get_settings
from app.infra.db import engine
from app.main import app
from app.models import Activity, Athlete, Group, GroupMembership
from app.services.session import create_session_token

ALICE_ID = 999_000_401
BOB_ID = 999_000_402      # member with no activities
CAROL_ID = 999_000_403    # not a member, but has activities
SEEDED = (ALICE_ID, BOB_ID, CAROL_ID)

settings = get_settings()


def check(label: str, condition: bool, detail: str = "") -> None:
    assert condition, f"{label} FAILED {detail}"
    print(f"  ✓ {label}{(' — ' + detail) if detail else ''}")


def cleanup() -> None:
    with Session(engine) as session:
        ids = [g.id for g in session.exec(select(Group).where(Group.created_by.in_(SEEDED))).all()]
        if ids:
            session.exec(delete(GroupMembership).where(GroupMembership.group_id.in_(ids)))
            session.exec(delete(Group).where(Group.id.in_(ids)))
        session.exec(delete(Activity).where(Activity.owner_id.in_(SEEDED)))
        session.exec(delete(GroupMembership).where(GroupMembership.athlete_id.in_(SEEDED)))
        session.exec(delete(Athlete).where(Athlete.athlete_id.in_(SEEDED)))
        session.commit()


def activity(activity_id: int, owner_id: int, days_ago: float, **kw) -> Activity:
    payload = {
        "sport_type": "Run",
        "distance": 5000.0,
        "moving_time": 1500,
        "elapsed_time": 1600,
        "total_elevation_gain": 50.0,
        "average_heartrate": 150.0,
    }
    payload.update(kw)
    return Activity(
        id=activity_id,
        owner_id=owner_id,
        name=f"Activity {activity_id}",
        start_date=datetime.now(UTC) - timedelta(days=days_ago),
        raw_data={"id": activity_id},
        **payload,
    )


def seed() -> int:
    cleanup()
    with Session(engine) as session:
        for athlete_id, name in ((ALICE_ID, "Alice"), (BOB_ID, "Bob"), (CAROL_ID, "Carol")):
            session.add(
                Athlete(
                    athlete_id=athlete_id,
                    name=name,
                    access_token="x",
                    refresh_token="x",
                    token_expires_at=datetime.now(UTC) + timedelta(hours=6),
                )
            )
        group = Group(name="Summary Test", invite_code="summary-test-1", created_by=ALICE_ID)
        session.add(group)
        session.commit()
        session.refresh(group)

        session.add(GroupMembership(group_id=group.id, athlete_id=ALICE_ID))
        session.add(GroupMembership(group_id=group.id, athlete_id=BOB_ID))

        # Alice: 2 runs + 1 ride inside the window, 1 run outside it.
        session.add(activity(4001, ALICE_ID, days_ago=1))
        session.add(activity(4002, ALICE_ID, days_ago=2, average_heartrate=160.0))
        session.add(activity(4003, ALICE_ID, days_ago=3, sport_type="Ride", distance=20000.0,
                             moving_time=3600, average_heartrate=None))
        session.add(activity(4004, ALICE_ID, days_ago=60))  # outside a 30-day window
        # Carol is NOT in the group but has activities — must never appear.
        session.add(activity(4005, CAROL_ID, days_ago=1, distance=99999.0))
        session.commit()
        return group.id


def main() -> None:
    group_id = seed()
    try:
        alice = TestClient(app)
        alice.cookies.set(settings.session_cookie_name, create_session_token(ALICE_ID))
        bob = TestClient(app)
        bob.cookies.set(settings.session_cookie_name, create_session_token(BOB_ID))
        carol = TestClient(app)
        carol.cookies.set(settings.session_cookie_name, create_session_token(CAROL_ID))
        anon = TestClient(app)

        print("\nsummary")
        r = alice.get(f"/groups/{group_id}/summary", params={"days": 30})
        check("200 for a member", r.status_code == 200, str(r.json())[:200])
        data = r.json()
        members = {m["athlete_id"]: m for m in data["members"]}
        check("every member present", set(members) == {ALICE_ID, BOB_ID})
        check("non-member's activities excluded", CAROL_ID not in members)

        a = members[ALICE_ID]
        check("counts only in-window activities", a["activity_count"] == 3, f"{a['activity_count']}")
        check("distance summed", a["total_distance"] == 30000.0, str(a["total_distance"]))
        check("moving time summed", a["total_moving_time"] == 6600, str(a["total_moving_time"]))
        check("elevation summed", a["total_elevation_gain"] == 150.0)

        sports = {s["sport_type"]: s for s in a["by_sport"]}
        check("split by sport", set(sports) == {"Run", "Ride"})
        check("per-sport counts", sports["Run"]["activity_count"] == 2 and sports["Ride"]["activity_count"] == 1)
        check("per-sport HR averaged", sports["Run"]["avg_heartrate"] == 155.0, str(sports["Run"]["avg_heartrate"]))
        check("HR null when unrecorded", sports["Ride"]["avg_heartrate"] is None)
        check("overall HR ignores HR-less activities", a["avg_heartrate"] == 155.0, str(a["avg_heartrate"]))

        b = members[BOB_ID]
        check("inactive member included with zeroes",
              b["activity_count"] == 0 and b["total_distance"] == 0.0 and b["by_sport"] == [])

        check("ordered by moving time, most active first",
              [m["athlete_id"] for m in data["members"]] == [ALICE_ID, BOB_ID])

        print("\nwindow")
        r = alice.get(f"/groups/{group_id}/summary", params={"days": 90})
        wide = {m["athlete_id"]: m for m in r.json()["members"]}
        check("wider window picks up the older activity", wide[ALICE_ID]["activity_count"] == 4)
        r = alice.get(f"/groups/{group_id}/summary", params={"days": 0})
        check("days=0 rejected", r.status_code == 422)
        r = alice.get(f"/groups/{group_id}/summary", params={"days": 400})
        check("days>365 rejected", r.status_code == 422)

        print("\ntrend")
        r = alice.get(f"/groups/{group_id}/trend", params={"days": 30})
        check("200", r.status_code == 200)
        trend = {m["athlete_id"]: m for m in r.json()["members"]}
        check("every member present", set(trend) == {ALICE_ID, BOB_ID})
        check("inactive member has no weeks", trend[BOB_ID]["weeks"] == [])
        total = sum(w["activity_count"] for w in trend[ALICE_ID]["weeks"])
        check("weekly counts sum to the window total", total == 3, str(total))
        alice_weeks = trend[ALICE_ID]["weeks"]
        check("weeks carry a per-sport breakdown", all("by_sport" in w for w in alice_weeks))
        check(
            "per-sport counts sum to the week total",
            all(sum(b["activity_count"] for b in w["by_sport"]) == w["activity_count"] for w in alice_weeks),
            str(alice_weeks),
        )
        sports_seen = {b["sport_type"] for w in alice_weeks for b in w["by_sport"]}
        check("both sports present in the breakdown", sports_seen == {"Run", "Ride"}, str(sports_seen))
        check(
            "per-sport moving time sums to the week total",
            all(sum(b["total_moving_time"] for b in w["by_sport"]) == w["total_moving_time"] for w in alice_weeks),
        )
        check("weeks are chronological",
              [w["week_start"] for w in trend[ALICE_ID]["weeks"]]
              == sorted(w["week_start"] for w in trend[ALICE_ID]["weeks"]))

        print("\nfeed")
        r = alice.get(f"/groups/{group_id}/feed")
        check("200 for a member", r.status_code == 200, str(r.json())[:150])
        feed = r.json()
        ids = [i["activity_id"] for i in feed["items"]]
        check("all of the group's activities, any age", set(ids) == {4001, 4002, 4003, 4004}, str(ids))
        check("non-member's activity excluded", 4005 not in ids)
        check("newest first",
              [i["start_date"] for i in feed["items"]]
              == sorted((i["start_date"] for i in feed["items"]), reverse=True))
        check("athlete name attached", all(i["athlete_name"] == "Alice" for i in feed["items"]))
        check("visual fields present", all("polyline" in i and "photo_url" in i for i in feed["items"]))
        check("no polyline for GPS-less seeded activities",
              all(i["polyline"] is None for i in feed["items"]))
        check("no next page when everything fits", feed["next_before"] is None)

        r = alice.get(f"/groups/{group_id}/feed", params={"limit": 2})
        page1 = r.json()
        check("limit respected", len(page1["items"]) == 2)
        check("cursor returned when more exist", page1["next_before"] is not None)
        r = alice.get(f"/groups/{group_id}/feed", params={"limit": 2, "before": page1["next_before"]})
        page2 = r.json()
        page1_ids = [i["activity_id"] for i in page1["items"]]
        page2_ids = [i["activity_id"] for i in page2["items"]]
        check("second page has no overlap", not set(page1_ids) & set(page2_ids), f"{page1_ids} {page2_ids}")
        check("pages cover everything", set(page1_ids) | set(page2_ids) == {4001, 4002, 4003, 4004})
        check("limit bounds enforced",
              alice.get(f"/groups/{group_id}/feed", params={"limit": 0}).status_code == 422
              and alice.get(f"/groups/{group_id}/feed", params={"limit": 500}).status_code == 422)

        print("\nactivity detail")
        r = alice.get("/activities/4001")
        check("owner can view", r.status_code == 200, str(r.json())[:150])
        detail = r.json()
        check("athlete name attached", detail["athlete_name"] == "Alice")
        check("stored fields returned", detail["distance"] == 5000.0)
        check("no polyline for a GPS-less activity", detail["polyline"] is None)
        check("flagged as not fully detailed", detail["is_detailed"] is False)

        r = bob.get("/activities/4001")
        check("groupmate can view", r.status_code == 200)
        r = carol.get("/activities/4001")
        check("non-groupmate → 403", r.status_code == 403, str(r.json()))
        r = alice.get("/activities/4005")
        check("cannot view a stranger's activity → 403", r.status_code == 403)
        r = alice.get("/activities/99999999")
        check("missing activity → 404", r.status_code == 404)
        r = anon.get("/activities/4001")
        check("anonymous → 401", r.status_code == 401)

        print("\naccess control")
        check("non-member → 403", carol.get(f"/groups/{group_id}/summary").status_code == 403)
        check("non-member trend → 403", carol.get(f"/groups/{group_id}/trend").status_code == 403)
        check("anonymous → 401", anon.get(f"/groups/{group_id}/summary").status_code == 401)
        check("missing group → 404", alice.get("/groups/99999999/summary").status_code == 404)
        check("non-member feed → 403", carol.get(f"/groups/{group_id}/feed").status_code == 403)
        check("anonymous feed → 401", anon.get(f"/groups/{group_id}/feed").status_code == 401)
    finally:
        cleanup()

    print("\nPhase 8 summary checks OK")


if __name__ == "__main__":
    main()
