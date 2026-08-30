"""Push checkpoint: subscriptions, delivery, and the encryption in between.

Stands up a throwaway HTTP server that plays the part of Apple's push service, subscribes
a fake browser to it, and decrypts what arrives — so the whole path is exercised without a
phone in the loop.

Run with:  .venv/bin/python -m scripts.check_push
"""

import base64
import json
import os
import threading
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer

import http_ece
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient
from sqlmodel import Session, delete, select

from app.config import get_settings
from app.infra.db import engine
from app.main import app
from app.models import (
    Activity,
    Athlete,
    Group,
    GroupMembership,
    GroupTarget,
    PushDayNotification,
    PushSubscription,
)
from app.schemas.push import PushKeys, PushSubscriptionWrite
from app.services.push import notify_activity, save_subscription
from app.services.session import create_session_token

ANNA_ID = 999_000_701
BEN_ID = 999_000_702
CARL_ID = 999_000_703
SEEDED = (ANNA_ID, BEN_ID, CARL_ID)

settings = get_settings()


def check(label: str, condition: bool, detail: str = "") -> None:
    assert condition, f"{label} FAILED {detail}"
    print(f"  ✓ {label}{(' — ' + detail) if detail else ''}")


def b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


class FakeBrowser:
    """The keys a real browser generates when it subscribes."""

    def __init__(self) -> None:
        self.private_key = ec.generate_private_key(ec.SECP256R1())
        numbers = self.private_key.public_key().public_numbers()
        self.public_raw = b"\x04" + numbers.x.to_bytes(32, "big") + numbers.y.to_bytes(32, "big")
        self.auth_secret = os.urandom(16)

    @property
    def p256dh(self) -> str:
        return b64(self.public_raw)

    @property
    def auth(self) -> str:
        return b64(self.auth_secret)

    def decrypt(self, body: bytes) -> dict:
        plaintext = http_ece.decrypt(
            body,
            private_key=self.private_key,
            auth_secret=self.auth_secret,
            version="aes128gcm",
        )
        return json.loads(plaintext)


class Capture(BaseHTTPRequestHandler):
    """Stands in for the push service: records the request, answers as told."""

    received: list[tuple[dict, bytes]] = []
    status = 201

    def do_POST(self) -> None:  # noqa: N802 - http.server's naming
        length = int(self.headers.get("content-length", 0))
        Capture.received.append((dict(self.headers), self.rfile.read(length)))
        self.send_response(Capture.status)
        self.end_headers()

    def log_message(self, *args) -> None:  # keep the checkpoint output clean
        return


def cleanup() -> None:
    with Session(engine) as session:
        ids = [g.id for g in session.exec(select(Group).where(Group.created_by.in_(SEEDED))).all()]
        if ids:
            session.exec(delete(GroupMembership).where(GroupMembership.group_id.in_(ids)))
            session.exec(delete(Group).where(Group.id.in_(ids)))
        session.exec(delete(PushDayNotification).where(PushDayNotification.athlete_id.in_(SEEDED)))
        session.exec(delete(PushSubscription).where(PushSubscription.athlete_id.in_(SEEDED)))
        session.exec(delete(GroupTarget).where(GroupTarget.group_id.in_(ids or [0])))
        session.exec(delete(Activity).where(Activity.owner_id.in_(SEEDED)))
        session.exec(delete(GroupMembership).where(GroupMembership.athlete_id.in_(SEEDED)))
        session.exec(delete(Athlete).where(Athlete.athlete_id.in_(SEEDED)))
        session.commit()


def seed() -> int:
    cleanup()
    now = datetime.now(UTC)
    with Session(engine) as session:
        for athlete_id, name in ((ANNA_ID, "Anna"), (BEN_ID, "Ben"), (CARL_ID, "Carl")):
            session.add(
                Athlete(
                    athlete_id=athlete_id,
                    name=name,
                    access_token="x",
                    refresh_token="x",
                    token_expires_at=now + timedelta(hours=6),
                )
            )
        group = Group(name="Push Test", invite_code="push-test-1", created_by=ANNA_ID)
        session.add(group)
        session.commit()
        session.refresh(group)

        session.add(GroupMembership(group_id=group.id, athlete_id=ANNA_ID))
        session.add(GroupMembership(group_id=group.id, athlete_id=BEN_ID))

        # Every sport asks for 45 minutes, like the real group's does.
        session.add(
            GroupTarget(
                group_id=group.id,
                count=2,
                period="week",
                starts_at=now - timedelta(days=30),
                until=now + timedelta(days=30),
                rules={"default_min_minutes": 45, "sports": {}},
            )
        )

        # Twenty minutes then twenty-five: neither reaches the bar, together they do.
        for index, minutes in enumerate((20, 25)):
            when = now - timedelta(hours=2 - index)
            session.add(
                Activity(
                    id=97_000_001 + index,
                    owner_id=ANNA_ID,
                    name="Morning Run" if index == 0 else "Lunch Run",
                    sport_type="Run",
                    distance=3000.0,
                    moving_time=minutes * 60,
                    elapsed_time=minutes * 60,
                    total_elevation_gain=0.0,
                    start_date=when,
                    start_date_local=when.replace(tzinfo=None),
                    utc_offset=0,
                    raw_data={},
                )
            )
        session.commit()
        return group.id


def main() -> None:
    check("the server has VAPID keys", bool(settings.vapid_private_key), "from .env")

    group_id = seed()
    server = HTTPServer(("127.0.0.1", 0), Capture)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    endpoint = f"http://127.0.0.1:{server.server_port}/push/anna"

    try:
        browser = FakeBrowser()

        print("\nsubscribing")
        with Session(engine) as session:
            body = PushSubscriptionWrite(
                endpoint=endpoint, keys=PushKeys(p256dh=browser.p256dh, auth=browser.auth)
            )
            save_subscription(session, ANNA_ID, body, "iPhone")
            check("a device is stored", session.get(PushSubscription, endpoint) is not None)

            save_subscription(session, ANNA_ID, body, "iPhone")
            rows = session.exec(
                select(PushSubscription).where(PushSubscription.athlete_id == ANNA_ID)
            ).all()
            check("re-subscribing the same device does not duplicate it", len(rows) == 1)

        print("\nonly when the day's target is reached")
        Capture.received.clear()
        with Session(engine) as session:
            # The first workout leaves the day at 20 of the 45 minutes asked for.
            first = session.get(Activity, 97_000_002)
            session.delete(first)
            session.commit()
            delivered = notify_activity(session, 97_000_001)
        check("a workout that leaves the day short sends nothing", delivered == 0)
        check("and nothing reaches the push service", len(Capture.received) == 0)

        with Session(engine) as session:
            when = datetime.now(UTC) - timedelta(hours=1)
            session.add(
                Activity(
                    id=97_000_002,
                    owner_id=ANNA_ID,
                    name="Lunch Run",
                    sport_type="Run",
                    distance=3000.0,
                    moving_time=25 * 60,
                    elapsed_time=25 * 60,
                    total_elevation_gain=0.0,
                    start_date=when,
                    start_date_local=when.replace(tzinfo=None),
                    utc_offset=0,
                    raw_data={},
                )
            )
            session.commit()
            delivered = notify_activity(session, 97_000_002)
        check("the one that crosses the bar does send", delivered == 1,
              "20 + 25 minutes against a 45-minute target")
        check("the push service received a request", len(Capture.received) == 1)

        print("\nonce a day, whatever else happens")
        Capture.received.clear()
        with Session(engine) as session:
            delivered = notify_activity(session, 97_000_002)
        check("the same activity again sends nothing", delivered == 0, "a Strava update event")

        with Session(engine) as session:
            when = datetime.now(UTC)
            session.add(
                Activity(
                    id=97_000_003,
                    owner_id=ANNA_ID,
                    name="Evening Run",
                    sport_type="Run",
                    distance=9000.0,
                    moving_time=60 * 60,
                    elapsed_time=60 * 60,
                    total_elevation_gain=0.0,
                    start_date=when,
                    start_date_local=when.replace(tzinfo=None),
                    utc_offset=0,
                    raw_data={},
                )
            )
            session.commit()
            delivered = notify_activity(session, 97_000_003)
        check("a third workout the same day sends nothing", delivered == 0,
              "the target was already reached today")

        Capture.received.clear()
        with Session(engine) as session:
            # A fresh day, so the claim from earlier does not apply.
            session.exec(delete(PushDayNotification).where(PushDayNotification.athlete_id == ANNA_ID))
            session.commit()
            notify_activity(session, 97_000_002)

        headers, payload = Capture.received[0]
        check("signed with VAPID", headers.get("authorization", "").startswith("vapid "),
              headers.get("authorization", "")[:12])
        check("encrypted with aes128gcm", headers.get("content-encoding") == "aes128gcm")
        check("carries a TTL", headers.get("ttl") == "86400", "a day, so a night's sleep is fine")

        decrypted = browser.decrypt(payload)
        check("the browser can decrypt it", isinstance(decrypted, dict))
        check("it says the target was reached",
              decrypted["title"] == "Anna has reached today's target!", decrypted["title"])
        check("the body sums up the day", decrypted["body"].endswith("min today"),
              decrypted["body"])
        check("it deep-links to the activity",
              decrypted["url"] == f"/groups/{group_id}/activities/97000002", decrypted["url"])

        with Session(engine) as session:
            row = session.get(PushSubscription, endpoint)
            check("the device is marked as used", row.last_used_at is not None)

        print("\na device that has gone away")
        Capture.status = 410
        Capture.received.clear()
        with Session(engine) as session:
            session.exec(delete(PushDayNotification).where(PushDayNotification.athlete_id == ANNA_ID))
            session.commit()
            delivered = notify_activity(session, 97_000_002)
        check("nothing is delivered", delivered == 0)
        with Session(engine) as session:
            check("and the dead subscription is dropped",
                  session.get(PushSubscription, endpoint) is None,
                  "410 means the phone is gone for good")
        Capture.status = 201

        print("\napi")
        anna = TestClient(app)
        anna.cookies.set(settings.session_cookie_name, create_session_token(ANNA_ID))
        anon = TestClient(app)

        config = anna.get("/push/config")
        check("config is public", anon.get("/push/config").status_code == 200)
        check("it hands out the public key", len(config.json()["public_key"]) > 80)
        check("and says push is on", config.json()["enabled"] is True)

        subscription = {
            "endpoint": endpoint,
            "keys": {"p256dh": browser.p256dh, "auth": browser.auth},
        }
        check("subscribing needs a session",
              anon.post("/push/subscriptions", json=subscription).status_code == 401)
        check("POST → 200", anna.post("/push/subscriptions", json=subscription).status_code == 200)
        check("the device is listed", len(anna.get("/push/subscriptions").json()) == 1)

        Capture.received.clear()
        result = anna.post("/push/test")
        check("a test reaches the device", result.json()["delivered"] == 1, str(result.json()))

        check("DELETE → 204",
              anna.request("DELETE", "/push/subscriptions", json=subscription).status_code == 204)
        check("the device is gone", anna.get("/push/subscriptions").json() == [])
        check("deleting it again → 404",
              anna.request("DELETE", "/push/subscriptions", json=subscription).status_code == 404)

        print("\nPush checks OK")
    finally:
        server.shutdown()
        cleanup()


if __name__ == "__main__":
    main()
