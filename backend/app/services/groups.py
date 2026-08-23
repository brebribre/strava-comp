"""Group creation, joining and membership queries."""

import secrets

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, func, select

from app.models import Athlete, Group, GroupMembership
from app.services.errors import GroupNotFound

INVITE_CODE_BYTES = 6  # secrets.token_urlsafe(6) -> 8 url-safe characters
_MAX_CODE_ATTEMPTS = 5


def _generate_invite_code() -> str:
    return secrets.token_urlsafe(INVITE_CODE_BYTES)


def create_group(session: Session, name: str, creator_id: int) -> Group:
    """Create a group and add the creator as its first member."""
    for _ in range(_MAX_CODE_ATTEMPTS):
        group = Group(name=name, invite_code=_generate_invite_code(), created_by=creator_id)
        session.add(group)
        try:
            session.commit()
        except IntegrityError:
            # Invite code collision — vanishingly unlikely, but cheap to retry.
            session.rollback()
            continue
        session.refresh(group)
        session.add(GroupMembership(group_id=group.id, athlete_id=creator_id))
        session.commit()
        session.refresh(group)
        return group
    raise RuntimeError("could not generate a unique invite code")


def join_group(session: Session, invite_code: str, athlete_id: int) -> Group:
    """Add an athlete to the group with this invite code.

    Idempotent: joining twice is a no-op rather than an error, so a shared link can
    be clicked repeatedly.
    """
    group = session.exec(select(Group).where(Group.invite_code == invite_code)).first()
    if group is None:
        raise GroupNotFound(f"no group with invite code {invite_code!r}")

    already = session.get(GroupMembership, (group.id, athlete_id))
    if already is None:
        session.add(GroupMembership(group_id=group.id, athlete_id=athlete_id))
        session.commit()
        session.refresh(group)
    return group


def is_member(session: Session, group_id: int, athlete_id: int) -> bool:
    return session.get(GroupMembership, (group_id, athlete_id)) is not None


def member_count(session: Session, group_id: int) -> int:
    return session.exec(
        select(func.count())
        .select_from(GroupMembership)
        .where(GroupMembership.group_id == group_id)
    ).one()


def list_groups_for_athlete(session: Session, athlete_id: int) -> list[tuple[Group, int]]:
    """Every group the athlete belongs to, paired with its member count."""
    rows = session.exec(
        select(Group, func.count(GroupMembership.athlete_id))
        .join(GroupMembership, GroupMembership.group_id == Group.id)
        .where(
            Group.id.in_(
                select(GroupMembership.group_id).where(GroupMembership.athlete_id == athlete_id)
            )
        )
        .group_by(Group.id)
        .order_by(Group.created_at)
    ).all()
    return [(group, count) for group, count in rows]


def list_members(session: Session, group_id: int) -> list[tuple[Athlete, GroupMembership]]:
    return session.exec(
        select(Athlete, GroupMembership)
        .join(GroupMembership, GroupMembership.athlete_id == Athlete.athlete_id)
        .where(GroupMembership.group_id == group_id)
        .order_by(GroupMembership.joined_at)
    ).all()
