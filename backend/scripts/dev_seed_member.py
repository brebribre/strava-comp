"""Dev helper: add a fake athlete to a group, so multi-member flows can be tested solo.

    .venv/bin/python -m scripts.dev_seed_member <invite_code> [name]
    .venv/bin/python -m scripts.dev_seed_member --remove

Fake athletes get IDs in the 999_00x_xxx range and carry no usable Strava tokens,
so they will never be picked up by real activity syncing.
"""

import sys
from datetime import UTC, datetime, timedelta

from sqlmodel import Session, delete, select

from app.infra.db import engine
from app.models import Athlete, Group, GroupMembership
from app.services import groups as groups_service
from app.services.errors import GroupNotFound

DEV_ID_BASE = 999_100_000


def remove_all() -> None:
    with Session(engine) as session:
        fake_ids = [
            a.athlete_id
            for a in session.exec(select(Athlete).where(Athlete.athlete_id >= DEV_ID_BASE)).all()
        ]
        if not fake_ids:
            print("no dev athletes to remove")
            return
        session.exec(delete(GroupMembership).where(GroupMembership.athlete_id.in_(fake_ids)))
        session.exec(delete(Athlete).where(Athlete.athlete_id.in_(fake_ids)))
        session.commit()
        print(f"removed {len(fake_ids)} dev athlete(s): {fake_ids}")


def add(invite_code: str, name: str) -> None:
    with Session(engine) as session:
        existing = session.exec(
            select(Athlete).where(Athlete.athlete_id >= DEV_ID_BASE).order_by(Athlete.athlete_id.desc())
        ).first()
        athlete_id = (existing.athlete_id + 1) if existing else DEV_ID_BASE + 1

        session.add(
            Athlete(
                athlete_id=athlete_id,
                name=name,
                access_token="dev-no-token",
                refresh_token="dev-no-token",
                token_expires_at=datetime.now(UTC) - timedelta(days=365),
            )
        )
        session.commit()

        try:
            group = groups_service.join_group(session, invite_code, athlete_id)
        except GroupNotFound:
            session.exec(delete(Athlete).where(Athlete.athlete_id == athlete_id))
            session.commit()
            print(f"no group with invite code {invite_code!r}")
            sys.exit(1)

        members = groups_service.list_members(session, group.id)
        print(f"added {name} ({athlete_id}) to group {group.id} '{group.name}'")
        print("members now:")
        for athlete, membership in members:
            tag = "  (dev)" if athlete.athlete_id >= DEV_ID_BASE else ""
            print(f"  {athlete.athlete_id:>12}  {athlete.name}{tag}")


if __name__ == "__main__":
    if "--remove" in sys.argv:
        remove_all()
    elif len(sys.argv) >= 2:
        add(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "Dev Brother")
    else:
        print(__doc__)
        sys.exit(1)
