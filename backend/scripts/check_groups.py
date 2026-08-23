"""Phase 5 checkpoint: groups create/join/list and membership enforcement.

Uses two seeded athletes with real signed session cookies, so a second Strava
account isn't needed for development.

Run with:  .venv/bin/python -m scripts.check_groups
"""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session, delete

from app.config import get_settings
from app.infra.db import engine
from app.main import app
from app.models import Athlete, Group, GroupMembership
from app.services.session import create_session_token

ALICE_ID = 999_000_101
BOB_ID = 999_000_102
CAROL_ID = 999_000_103
SEEDED = (ALICE_ID, BOB_ID, CAROL_ID)

settings = get_settings()


def check(label: str, condition: bool, detail: str = "") -> None:
    assert condition, f"{label} FAILED {detail}"
    print(f"  ✓ {label}{(' — ' + detail) if detail else ''}")


def cleanup() -> None:
    with Session(engine) as session:
        group_ids = [
            g.id for g in session.exec(select_seeded_groups()).all()
        ]
        if group_ids:
            session.exec(delete(GroupMembership).where(GroupMembership.group_id.in_(group_ids)))
            session.exec(delete(Group).where(Group.id.in_(group_ids)))
        session.exec(delete(GroupMembership).where(GroupMembership.athlete_id.in_(SEEDED)))
        session.exec(delete(Athlete).where(Athlete.athlete_id.in_(SEEDED)))
        session.commit()


def select_seeded_groups():
    from sqlmodel import select

    return select(Group).where(Group.created_by.in_(SEEDED))


def seed() -> None:
    cleanup()
    with Session(engine) as session:
        for athlete_id, name in ((ALICE_ID, "Alice"), (BOB_ID, "Bob"), (CAROL_ID, "Carol")):
            session.add(
                Athlete(
                    athlete_id=athlete_id,
                    name=name,
                    access_token=f"access-{athlete_id}",
                    refresh_token=f"refresh-{athlete_id}",
                    token_expires_at=datetime.now(UTC) + timedelta(hours=6),
                )
            )
        session.commit()


def client_for(athlete_id: int) -> TestClient:
    client = TestClient(app)
    client.cookies.set(settings.session_cookie_name, create_session_token(athlete_id))
    return client


def main() -> None:
    seed()
    try:
        alice, bob, carol = client_for(ALICE_ID), client_for(BOB_ID), client_for(CAROL_ID)
        anon = TestClient(app)

        print("\ncreate")
        r = alice.post("/groups", json={"name": "Alvin Brothers"})
        check("201 created", r.status_code == 201, str(r.json()))
        group = r.json()
        check("invite code generated", len(group["invite_code"]) >= 8, group["invite_code"])
        check("creator recorded", group["created_by"] == ALICE_ID)
        check("creator auto-joined", group["member_count"] == 1)
        group_id, code = group["id"], group["invite_code"]

        r = alice.post("/groups", json={"name": "Second Group"})
        check("codes differ between groups", r.json()["invite_code"] != code)
        second_id = r.json()["id"]

        r = alice.post("/groups", json={"name": ""})
        check("empty name rejected", r.status_code == 422)

        print("\njoin")
        r = bob.post("/groups/join", json={"invite_code": code})
        check("bob joins", r.status_code == 200 and r.json()["member_count"] == 2)

        r = bob.post("/groups/join", json={"invite_code": code})
        check("re-join is idempotent", r.status_code == 200 and r.json()["member_count"] == 2)

        r = bob.post("/groups/join", json={"invite_code": "nope-nope"})
        check("bad code → 404", r.status_code == 404)

        print("\nlist")
        r = alice.get("/groups")
        check("alice sees both her groups", {g["id"] for g in r.json()} == {group_id, second_id})
        r = bob.get("/groups")
        check("bob sees only the one he joined", [g["id"] for g in r.json()] == [group_id])
        r = carol.get("/groups")
        check("carol sees none", r.json() == [])

        print("\nmembers")
        r = alice.get(f"/groups/{group_id}/members")
        check("200 for a member", r.status_code == 200)
        members = r.json()
        check("both members listed", {m["athlete_id"] for m in members} == {ALICE_ID, BOB_ID})
        check("names included", {m["name"] for m in members} == {"Alice", "Bob"})
        check("ordered by joined_at", [m["athlete_id"] for m in members] == [ALICE_ID, BOB_ID])
        r = bob.get(f"/groups/{group_id}/members")
        check("member-only view is shared, not caller-only", len(r.json()) == 2)

        print("\nenforcement (require_group_member)")
        r = carol.get(f"/groups/{group_id}/members")
        check("non-member → 403", r.status_code == 403, str(r.json()))
        r = bob.get(f"/groups/{second_id}/members")
        check("member of another group → 403", r.status_code == 403)
        r = alice.get("/groups/99999999/members")
        check("missing group → 404", r.status_code == 404)
        r = anon.get(f"/groups/{group_id}/members")
        check("anonymous → 401", r.status_code == 401)
        r = anon.post("/groups", json={"name": "x"})
        check("anonymous cannot create", r.status_code == 401)
        r = anon.get("/groups")
        check("anonymous cannot list", r.status_code == 401)

        print("\ninvite code privacy")
        r = carol.post("/groups/join", json={"invite_code": code})
        check("carol can join with the code", r.status_code == 200)
        r = carol.get(f"/groups/{group_id}/members")
        check("carol now allowed", r.status_code == 200 and len(r.json()) == 3)
    finally:
        cleanup()

    print("\nPhase 5 groups OK")


if __name__ == "__main__":
    main()
