"""Phase 2 checkpoint: insert fake rows, read them back through the real joins, clean up.

Run with:  .venv/bin/python -m scripts.check_schema_roundtrip
"""

from datetime import UTC, datetime, timedelta

from sqlmodel import Session, delete, select

from app.infra.db import engine, run_migrations
from app.models import Activity, Athlete, Group, GroupMembership

FAKE_ATHLETE_ID = 999_000_001
FAKE_ACTIVITY_ID = 14_000_000_000_001  # deliberately > int32, like real Strava IDs


def main() -> None:
    run_migrations()

    with Session(engine) as session:
        # --- clean any leftovers from a previous run -------------------------
        session.exec(delete(Activity).where(Activity.owner_id == FAKE_ATHLETE_ID))
        session.exec(delete(GroupMembership).where(GroupMembership.athlete_id == FAKE_ATHLETE_ID))
        session.exec(delete(Group).where(Group.invite_code == "test-code-1"))
        session.exec(delete(Athlete).where(Athlete.athlete_id == FAKE_ATHLETE_ID))
        session.commit()

        # --- insert ----------------------------------------------------------
        athlete = Athlete(
            athlete_id=FAKE_ATHLETE_ID,
            name="Test Athlete",
            access_token="fake-access",
            refresh_token="fake-refresh",
            token_expires_at=datetime.now(UTC) + timedelta(hours=6),
        )
        session.add(athlete)
        session.commit()

        group = Group(name="Test Group", invite_code="test-code-1", created_by=FAKE_ATHLETE_ID)
        session.add(group)
        session.commit()
        session.refresh(group)

        session.add(GroupMembership(group_id=group.id, athlete_id=FAKE_ATHLETE_ID))
        session.add(
            Activity(
                id=FAKE_ACTIVITY_ID,
                owner_id=FAKE_ATHLETE_ID,
                name="Morning Run",
                sport_type="Run",
                distance=10_000.0,
                moving_time=3_000,
                elapsed_time=3_120,
                total_elevation_gain=120.5,
                average_heartrate=148.2,
                start_date=datetime.now(UTC) - timedelta(days=1),
                raw_data={"id": FAKE_ACTIVITY_ID, "type": "Run", "kudos_count": 3},
            )
        )
        session.commit()

        # --- read back -------------------------------------------------------
        stored = session.get(Athlete, FAKE_ATHLETE_ID)
        assert stored is not None and stored.name == "Test Athlete"
        assert stored.token_expires_at.tzinfo is not None, "timestamps must come back tz-aware"
        print(f"athlete       : {stored.athlete_id} {stored.name} expires={stored.token_expires_at}")

        act = session.get(Activity, FAKE_ACTIVITY_ID)
        assert act is not None and act.raw_data["kudos_count"] == 3, "JSONB round-trip failed"
        print(f"activity      : {act.id} {act.sport_type} {act.distance}m raw_data={act.raw_data}")

        # The Phase 8 shape: activities joined to athletes via group membership.
        rows = session.exec(
            select(Athlete.name, Activity.sport_type, Activity.distance)
            .join(GroupMembership, GroupMembership.athlete_id == Athlete.athlete_id)
            .join(Activity, Activity.owner_id == Athlete.athlete_id)
            .where(GroupMembership.group_id == group.id)
        ).all()
        assert rows == [("Test Athlete", "Run", 10_000.0)], rows
        print(f"group join    : group_id={group.id} invite={group.invite_code} rows={rows}")

        # --- constraints -----------------------------------------------------
        try:
            session.add(Group(name="Dup", invite_code="test-code-1", created_by=FAKE_ATHLETE_ID))
            session.commit()
            raise AssertionError("duplicate invite_code should have been rejected")
        except Exception as exc:
            session.rollback()
            assert "unique" in str(exc).lower(), exc
            print("unique code   : duplicate invite_code rejected ✓")

        # Deleting the athlete cascades to activities and memberships, and leaves
        # the group standing with created_by nulled out.
        session.delete(session.get(Athlete, FAKE_ATHLETE_ID))
        session.commit()
        surviving = session.get(Group, group.id)
        assert surviving is not None and surviving.created_by is None, surviving
        print("group survives: creator deleted, created_by set to NULL ✓")
        session.exec(delete(Group).where(Group.id == group.id))
        session.commit()
        assert session.get(Activity, FAKE_ACTIVITY_ID) is None
        assert (
            session.exec(
                select(GroupMembership).where(GroupMembership.athlete_id == FAKE_ATHLETE_ID)
            ).first()
            is None
        )
        print("cascade delete: activities + memberships removed with athlete ✓")

    print("\nPhase 2 round-trip OK")


if __name__ == "__main__":
    main()
