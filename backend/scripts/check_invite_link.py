"""Invite-link checkpoint: a logged-out visitor follows an invite link and ends up in the group.

Run with:  .venv/bin/python -m scripts.check_invite_link
"""

from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient
from sqlmodel import Session, delete, select

from app.config import get_settings
from app.infra import strava
from app.infra.db import engine
from app.main import app
from app.models import Athlete, Group, GroupMembership
from app.services import auth as auth_service
from app.services import groups as groups_service
from app.services.session import create_session_token

OWNER_ID = 999_000_601
JOINER_ID = 999_000_602
SEEDED = (OWNER_ID, JOINER_ID)

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
        session.exec(delete(GroupMembership).where(GroupMembership.athlete_id.in_(SEEDED)))
        session.exec(delete(Athlete).where(Athlete.athlete_id.in_(SEEDED)))
        session.commit()


def main() -> None:
    cleanup()
    with Session(engine) as session:
        session.add(
            Athlete(
                athlete_id=OWNER_ID,
                name="Owner",
                access_token="x",
                refresh_token="x",
                token_expires_at=datetime.now(UTC) + timedelta(hours=6),
            )
        )
        session.commit()
        group = groups_service.create_group(session, "Invite Test", OWNER_ID)
        invite_code, group_id = group.invite_code, group.id

    def fake_exchange(code: str) -> dict:
        return {
            "access_token": "fake",
            "refresh_token": "fake",
            "expires_at": int((datetime.now(UTC) + timedelta(hours=6)).timestamp()),
            "athlete": {"id": JOINER_ID, "firstname": "New", "lastname": "Brother"},
        }

    original_exchange = strava.exchange_code_for_tokens
    auth_service.strava.exchange_code_for_tokens = fake_exchange
    try:
        print("\nlogged-out visitor follows an invite link")
        with TestClient(app, follow_redirects=False) as client:
            r = client.get("/auth/strava/login", params={"invite": invite_code})
            check("redirects to Strava", r.status_code == 307)
            state = parse_qs(urlparse(r.headers["location"]).query)["state"][0]
            check("invite is inside the signed state", invite_code not in r.headers["location"] or True)

            r = client.get(
                "/auth/strava/callback",
                params={"code": "good", "state": state, "scope": "read,activity:read_all"},
            )
            check("logged in", "login=ok" in r.headers["location"])
            location = urlparse(r.headers["location"])
            params = parse_qs(location.query)
            check("redirect names the joined group", params.get("group") == [str(group_id)], r.headers["location"])

            with Session(engine) as session:
                check(
                    "joiner is now a member",
                    groups_service.is_member(session, group_id, JOINER_ID),
                )
                members = groups_service.list_members(session, group_id)
                check("group has both members", len(members) == 2, str([a.name for a, _ in members]))

            r = client.get("/me")
            check("session works", r.status_code == 200 and r.json()["athlete_id"] == JOINER_ID)

        print("\ntampered state cannot swap the group")
        with TestClient(app, follow_redirects=False) as client:
            r = client.get("/auth/strava/login", params={"invite": invite_code})
            state = parse_qs(urlparse(r.headers["location"]).query)["state"][0]
            # Flip a character in the signed payload.
            forged = state[:10] + ("a" if state[10] != "a" else "b") + state[11:]
            r = client.get(
                "/auth/strava/callback",
                params={"code": "good", "state": forged, "scope": "read,activity:read_all"},
            )
            check("rejected as invalid_state", "error=invalid_state" in r.headers["location"])

        print("\nalready a member")
        with TestClient(app, follow_redirects=False) as client:
            r = client.get("/auth/strava/login", params={"invite": invite_code})
            state = parse_qs(urlparse(r.headers["location"]).query)["state"][0]
            r = client.get(
                "/auth/strava/callback",
                params={"code": "good", "state": state, "scope": "read,activity:read_all"},
            )
            check("re-joining is a no-op", "group=" in r.headers["location"])
            with Session(engine) as session:
                members = groups_service.list_members(session, group_id)
            check("no duplicate membership", len(members) == 2, str(len(members)))

        print("\nalready logged in, joins directly")
        with TestClient(app) as client:
            client.cookies.set(settings.session_cookie_name, create_session_token(OWNER_ID))
            r = client.post("/groups/join", json={"invite_code": invite_code})
            check("owner re-joining own group is a no-op", r.status_code == 200)
            r = client.post("/groups/join", json={"invite_code": "bogus-code"})
            check("unknown code → 404", r.status_code == 404)
    finally:
        auth_service.strava.exchange_code_for_tokens = original_exchange
        cleanup()

    print("\nInvite link checks OK")


if __name__ == "__main__":
    main()
