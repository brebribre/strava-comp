"""Phase 3 checkpoint: exercise the whole OAuth flow with Strava's token endpoint stubbed.

Everything except Strava's own consent screen is covered: the authorize redirect,
CSRF state validation, scope enforcement, athlete upsert, session cookie, /me and logout.

Run with:  .venv/bin/python -m scripts.check_auth_flow
"""

from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient
from sqlmodel import Session, delete

from app.config import get_settings
from app.infra import strava
from app.infra.db import engine
from app.main import app
from app.models import Athlete
from app.services import auth as auth_service

FAKE_ATHLETE_ID = 999_000_042
settings = get_settings()

TOKEN_PAYLOAD = {
    "access_token": "fake-access-token",
    "refresh_token": "fake-refresh-token",
    "expires_at": int((datetime.now(UTC) + timedelta(hours=6)).timestamp()),
    "athlete": {"id": FAKE_ATHLETE_ID, "firstname": "Test", "lastname": "Runner"},
}


def cleanup() -> None:
    with Session(engine) as session:
        session.exec(delete(Athlete).where(Athlete.athlete_id == FAKE_ATHLETE_ID))
        session.commit()


def check(label: str, condition: bool, detail: str = "") -> None:
    assert condition, f"{label} FAILED {detail}"
    print(f"  ✓ {label}{(' — ' + detail) if detail else ''}")


def main() -> None:
    cleanup()
    calls: list[str] = []

    # Stub Strava's token endpoint — everything else is the real code path.
    def fake_exchange(code: str) -> dict:
        calls.append(code)
        if code == "bad-code":
            raise strava.StravaError("token exchange failed (400)")
        return TOKEN_PAYLOAD

    original = strava.exchange_code_for_tokens
    auth_service.strava.exchange_code_for_tokens = fake_exchange
    try:
        with TestClient(app, follow_redirects=False) as client:
            print("\nauthorize redirect")
            r = client.get("/auth/strava/login")
            check("307 to strava.com", r.status_code == 307 and "strava.com/oauth/authorize" in r.headers["location"])
            qs = parse_qs(urlparse(r.headers["location"]).query)
            check("scope requests activity:read_all", "activity:read_all" in qs["scope"][0])
            check("redirect_uri matches config", qs["redirect_uri"][0] == settings.strava_redirect_uri)
            state = qs["state"][0]
            check("state cookie set", "sgt_oauth_state" in r.cookies)

            print("\ncallback rejections")
            r = client.get("/auth/strava/callback", params={"error": "access_denied"})
            check("user-denied → error=access_denied", r.status_code == 303 and "error=access_denied" in r.headers["location"])

            r = client.get("/auth/strava/callback", params={"code": "x", "state": "forged", "scope": "read,activity:read_all"})
            check("forged state rejected", "error=invalid_state" in r.headers["location"])

            r = client.get("/auth/strava/callback", params={"code": "x", "state": state, "scope": "read"})
            check("narrow scope rejected", "error=insufficient_scope" in r.headers["location"])

            r = client.get("/auth/strava/callback", params={"code": "bad-code", "state": state, "scope": "read,activity:read_all"})
            check("strava failure handled", "error=strava_exchange_failed" in r.headers["location"])
            check("no session cookie issued on failure", settings.session_cookie_name not in r.cookies)

            print("\ncallback success")
            r = client.get("/auth/strava/callback", params={"code": "good-code", "state": state, "scope": "read,activity:read_all"})
            check("303 to frontend", r.status_code == 303 and r.headers["location"].startswith(settings.frontend_origin))
            set_cookie = r.headers.get("set-cookie", "")
            check("session cookie is HttpOnly", "httponly" in set_cookie.lower())
            check("state cookie cleared", 'sgt_oauth_state=""' in set_cookie or "sgt_oauth_state=;" in set_cookie)

            with Session(engine) as session:
                stored = session.get(Athlete, FAKE_ATHLETE_ID)
                check("athlete row created", stored is not None, f"name={stored.name!r}")
                check("name from Strava payload", stored.name == "Test Runner")
                check("tokens stored", stored.access_token == "fake-access-token")

            print("\nsession")
            r = client.get("/me")
            check("/me returns 200", r.status_code == 200, str(r.json()))
            check("/me returns the athlete", r.json()["athlete_id"] == FAKE_ATHLETE_ID)
            check("/me leaks no tokens", "access_token" not in r.json() and "refresh_token" not in r.json())

            session_cookie = client.cookies[settings.session_cookie_name]
            tampered = session_cookie[:-1] + ("a" if session_cookie[-1] != "a" else "b")
            r = client.get("/me", headers={"Cookie": f"{settings.session_cookie_name}={tampered}"})
            check("tampered cookie → 401", r.status_code == 401)

            print("\ninvite link carried through OAuth")
            r = client.get("/auth/strava/login", params={"invite": "no-such-code"})
            invite_state = parse_qs(urlparse(r.headers["location"]).query)["state"][0]
            r = client.get(
                "/auth/strava/callback",
                params={"code": "good-code", "state": invite_state, "scope": "read,activity:read_all"},
            )
            check("bad invite still logs the user in", "login=ok" in r.headers["location"])
            check("bad invite reported, not fatal", "invite_error=not_found" in r.headers["location"])

            print("\nreturning user (upsert, not duplicate)")
            r = client.get("/auth/strava/login")
            state2 = parse_qs(urlparse(r.headers["location"]).query)["state"][0]
            TOKEN_PAYLOAD["access_token"] = "second-access-token"
            client.get("/auth/strava/callback", params={"code": "good-code", "state": state2, "scope": "read,activity:read_all"})
            with Session(engine) as session:
                stored = session.get(Athlete, FAKE_ATHLETE_ID)
                check("tokens updated in place", stored.access_token == "second-access-token")

            print("\nlogout")
            r = client.post("/auth/logout")
            check("logout 200", r.status_code == 200)
            r = client.get("/me")
            check("/me after logout → 401", r.status_code == 401)

            print("\ndeleted athlete with a valid cookie")
            client.cookies.set(settings.session_cookie_name, session_cookie)
            cleanup()
            r = client.get("/me")
            check("orphaned session → 401", r.status_code == 401)
    finally:
        auth_service.strava.exchange_code_for_tokens = original
        cleanup()

    print("\nPhase 3 auth flow OK")


if __name__ == "__main__":
    main()
