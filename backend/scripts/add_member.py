"""Add an already-logged-in athlete to a group, without them touching Swagger.

    .venv/bin/python -m scripts.add_member --list
    .venv/bin/python -m scripts.add_member <athlete_id> <invite_code>

Use --list after a brother logs in to find their athlete ID, then add them to the group.
"""

import sys

from sqlmodel import Session, select

from app.infra.db import engine
from app.models import Activity, Athlete, Group
from app.services import groups as groups_service
from app.services.errors import GroupNotFound


def list_state() -> None:
    with Session(engine) as session:
        print("athletes:")
        for a in session.exec(select(Athlete).order_by(Athlete.created_at)).all():
            count = len(session.exec(select(Activity).where(Activity.owner_id == a.athlete_id)).all())
            print(f"  {a.athlete_id:>12}  {a.name:<20} {count:>4} activities  joined {a.created_at:%Y-%m-%d}")
        print("\ngroups:")
        for g in session.exec(select(Group).order_by(Group.created_at)).all():
            members = groups_service.list_members(session, g.id)
            names = ", ".join(athlete.name for athlete, _ in members)
            print(f"  id={g.id}  {g.name!r}  invite={g.invite_code}  members: {names or '(none)'}")


def add(athlete_id: int, invite_code: str) -> None:
    with Session(engine) as session:
        athlete = session.get(Athlete, athlete_id)
        if athlete is None:
            print(f"no athlete {athlete_id} — have they logged in yet? try --list")
            sys.exit(1)
        try:
            group = groups_service.join_group(session, invite_code, athlete_id)
        except GroupNotFound:
            print(f"no group with invite code {invite_code!r}")
            sys.exit(1)
        members = groups_service.list_members(session, group.id)
        print(f"{athlete.name} is now in {group.name!r}. Members:")
        for a, _ in members:
            print(f"  {a.athlete_id:>12}  {a.name}")


if __name__ == "__main__":
    if "--list" in sys.argv:
        list_state()
    elif len(sys.argv) >= 3:
        add(int(sys.argv[1]), sys.argv[2])
    else:
        print(__doc__)
        sys.exit(1)
