"""Telegram notification checkpoint — no real messages are sent.

Run with:  .venv/bin/python -m scripts.check_notifications
"""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session, delete, select

from app.config import get_settings
from app.infra import telegram
from app.infra.db import engine
from app.main import app
from app.models import (
    Activity,
    ActivityNotification,
    Athlete,
    Group,
    GroupIntegration,
    GroupMembership,
    GroupTarget,
)
from app.services import notifications
from app.services.session import create_session_token

ALICE_ID = 999_000_701
BOB_ID = 999_000_702
CHAT_ID = -1009999999999
SEEDED = (ALICE_ID, BOB_ID)

settings = get_settings()


def check(label: str, condition: bool, detail: str = "") -> None:
    assert condition, f"{label} FAILED {detail}"
    print(f"  ✓ {label}{(' — ' + detail) if detail else ''}")


def cleanup() -> None:
    with Session(engine) as session:
        ids = [g.id for g in session.exec(select(Group).where(Group.created_by.in_(SEEDED))).all()]
        if ids:
            session.exec(delete(ActivityNotification).where(ActivityNotification.group_id.in_(ids)))
            session.exec(delete(GroupIntegration).where(GroupIntegration.group_id.in_(ids)))
            session.exec(delete(GroupTarget).where(GroupTarget.group_id.in_(ids)))
            session.exec(delete(GroupMembership).where(GroupMembership.group_id.in_(ids)))
            session.exec(delete(Group).where(Group.id.in_(ids)))
        session.exec(delete(Activity).where(Activity.owner_id.in_(SEEDED)))
        session.exec(delete(GroupMembership).where(GroupMembership.athlete_id.in_(SEEDED)))
        session.exec(delete(Athlete).where(Athlete.athlete_id.in_(SEEDED)))
        session.commit()


def seed() -> tuple[int, int]:
    cleanup()
    now = datetime.now(UTC)
    with Session(engine) as session:
        for athlete_id, name in ((ALICE_ID, "Alice Example"), (BOB_ID, "Bob Example")):
            session.add(
                Athlete(
                    athlete_id=athlete_id,
                    name=name,
                    access_token="x",
                    refresh_token="x",
                    token_expires_at=now + timedelta(hours=6),
                )
            )
        group = Group(name="Notify Test", invite_code="notify-test-1", created_by=ALICE_ID)
        session.add(group)
        session.commit()
        session.refresh(group)
        session.add(GroupMembership(group_id=group.id, athlete_id=ALICE_ID))

        long_activity = Activity(
            id=7_001, owner_id=ALICE_ID, name="Long Run", sport_type="Run",
            distance=8000.0, moving_time=2700, elapsed_time=2700,
            total_elevation_gain=20.0, average_heartrate=150.0,
            start_date=now - timedelta(hours=1), raw_data={"id": 7001},
        )
        short_activity = Activity(
            id=7_002, owner_id=ALICE_ID, name="Quick Jog", sport_type="Run",
            distance=800.0, moving_time=300, elapsed_time=300,
            total_elevation_gain=0.0, start_date=now, raw_data={"id": 7002},
        )
        session.add(long_activity)
        session.add(short_activity)
        session.commit()
        return group.id, long_activity.id


def main() -> None:
    group_id, activity_id = seed()
    sent: list[tuple[int, str]] = []

    def fake_send_photo(chat_id: int, image: bytes, caption: str, filename: str = "activity.png"):
        assert image[:4] == b"\x89PNG", "not a PNG"
        sent.append((chat_id, caption))
        return {"message_id": 1}

    original_photo = telegram.send_photo
    original_message = telegram.send_message
    notifications.telegram.send_photo = fake_send_photo

    try:
        print("\nno chat connected")
        with Session(engine) as session:
            check("nothing announced", notifications.announce_activity(session, activity_id) == 0)

        print("\nchat connected, no target")
        with Session(engine) as session:
            notifications.set_telegram_chat(session, group_id, CHAT_ID)
            check("announced", notifications.announce_activity(session, activity_id) == 1)
        check("sent to the right chat", sent[0][0] == CHAT_ID)
        check("caption names athlete and activity",
              sent[0][1] == "Alice Example just did Long Run!", sent[0][1])

        print("\ndedupe")
        with Session(engine) as session:
            check("second attempt does nothing", notifications.announce_activity(session, activity_id) == 0)
        check("only one message sent", len(sent) == 1)

        print("\ntarget qualification")
        sent.clear()
        with Session(engine) as session:
            session.add(
                GroupTarget(
                    group_id=group_id, count=3, period="week",
                    until=datetime.now(UTC) + timedelta(days=30),
                    rules={"default_min_minutes": 30, "sports": {"Run": {"min_minutes": 20, "min_distance_km": 3}}},
                )
            )
            session.commit()
            # 7_002 is 5 minutes and 800 m — below both thresholds.
            check("non-qualifying activity is skipped",
                  notifications.announce_activity(session, 7_002) == 0)
        check("nothing sent", sent == [])

        print("\nfailure handling")
        sent.clear()
        with Session(engine) as session:
            session.exec(delete(ActivityNotification).where(ActivityNotification.activity_id == activity_id))
            session.commit()

        def failing_send(chat_id, image, caption, filename="activity.png"):
            raise telegram.TelegramError("chat not found")

        notifications.telegram.send_photo = failing_send
        with Session(engine) as session:
            check("send failure reports zero", notifications.announce_activity(session, activity_id) == 0)
            check("claim released so a retry can work",
                  session.get(ActivityNotification, (activity_id, group_id)) is None)

        notifications.telegram.send_photo = fake_send_photo
        with Session(engine) as session:
            check("retry succeeds", notifications.announce_activity(session, activity_id) == 1)

        print("\npairing by code")
        with Session(engine) as session:
            notifications.set_telegram_chat(session, group_id, None)
            code = notifications.issue_pairing_code(session, group_id)
            check("code issued", len(code) == 6 and code.isalnum(), code)
            check("code is stable until used", notifications.issue_pairing_code(session, group_id) == code)

            check("unknown code connects nothing",
                  notifications.connect_by_code(session, "ZZZZZZ", -42, "Nope") is None)

            group = notifications.connect_by_code(session, code.lower(), -4242, "Family")
            check("case-insensitive match", group is not None and group.id == group_id)
            integration = notifications.get_integration(session, group_id)
            check("chat id stored", integration.telegram_chat_id == -4242)
            check("chat title stored", integration.telegram_chat_title == "Family")
            check("code rotated after use", integration.pairing_code != code,
                  "a forwarded message can't be replayed")

            check("disconnect by chat id",
                  notifications.disconnect_chat(session, -4242) is not None)
            check("chat cleared", notifications.get_integration(session, group_id).telegram_chat_id is None)

        print("\ntelegram webhook endpoint")
        client = TestClient(app)
        with Session(engine) as session:
            code = notifications.issue_pairing_code(session, group_id)

        sent_messages: list[tuple[int, str]] = []
        notifications.telegram.send_message = lambda chat_id, text: sent_messages.append((chat_id, text))
        import app.api.routes.telegram as telegram_route
        telegram_route.telegram.send_message = lambda chat_id, text: sent_messages.append((chat_id, text))

        payload = {"message": {"chat": {"id": -777, "title": "Chat", "type": "group"},
                               "text": f"/connect@BruderBandeBot {code}"}}
        r = client.post("/telegram/webhook", json=payload,
                        headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"})
        check("bad secret ignored", r.json()["status"] == "ignored")
        with Session(engine) as session:
            check("nothing connected", notifications.get_integration(session, group_id).telegram_chat_id is None)

        r = client.post("/telegram/webhook", json=payload,
                        headers={"X-Telegram-Bot-Api-Secret-Token": settings.telegram_webhook_secret})
        check("valid secret accepted", r.json()["status"] == "ok")
        with Session(engine) as session:
            check("connected via webhook",
                  notifications.get_integration(session, group_id).telegram_chat_id == -777)
        check("bot confirmed in chat", any("Notify Test" in text for _, text in sent_messages),
              str(sent_messages))

        print("\napi")
        client.cookies.set(settings.session_cookie_name, create_session_token(ALICE_ID))
        r = client.get(f"/groups/{group_id}/telegram")
        body = r.json()
        check("settings readable", r.status_code == 200 and body["is_configured"] is True)
        check("chat title exposed", body["chat_title"] == "Chat")
        check("pairing code always available", bool(body["pairing_code"]))

        r = client.delete(f"/groups/{group_id}/telegram")
        check("can disconnect", r.status_code == 200 and r.json()["is_configured"] is False)

        r = client.post(f"/groups/{group_id}/telegram/test")
        check("test with no chat → 400", r.status_code == 400, str(r.json()))

        anon = TestClient(app)
        check("anonymous → 401", anon.get(f"/groups/{group_id}/telegram").status_code == 401)

        bob = TestClient(app)
        bob.cookies.set(settings.session_cookie_name, create_session_token(BOB_ID))
        check("non-member → 403", bob.get(f"/groups/{group_id}/telegram").status_code == 403)
    finally:
        notifications.telegram.send_photo = original_photo
        notifications.telegram.send_message = original_message
        cleanup()

    print("\nNotification checks OK")


if __name__ == "__main__":
    main()
