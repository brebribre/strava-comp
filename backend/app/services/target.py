"""Group training targets: storage, qualification rules, and progress."""

from calendar import monthrange
from datetime import UTC, datetime, timedelta

from sqlmodel import Session, select

from app.models import Activity, Athlete, Group, GroupMembership, GroupTarget
from app.models.base import utcnow
from app.schemas.target import (
    MemberProgress,
    TargetProgress,
    TargetRead,
    TargetRules,
    TargetWrite,
)
from app.services.errors import GroupNotFound


def get_target(session: Session, group_id: int) -> GroupTarget | None:
    return session.get(GroupTarget, group_id)


def to_read(target: GroupTarget) -> TargetRead:
    return TargetRead(
        group_id=target.group_id,
        count=target.count,
        period=target.period,
        until=target.until,
        rules=TargetRules.model_validate(target.rules),
        created_at=target.created_at,
        updated_at=target.updated_at,
    )


def upsert_target(session: Session, group_id: int, data: TargetWrite) -> GroupTarget:
    """Create or replace the group's target. One target per group, so this is a replace."""
    if session.get(Group, group_id) is None:
        raise GroupNotFound(f"no group {group_id}")

    target = session.get(GroupTarget, group_id)
    if target is None:
        target = GroupTarget(
            group_id=group_id,
            count=data.count,
            period=data.period,
            until=data.until,
            rules=data.rules.model_dump(),
        )
    else:
        target.count = data.count
        target.period = data.period
        target.until = data.until
        target.rules = data.rules.model_dump()
        target.updated_at = utcnow()

    session.add(target)
    session.commit()
    session.refresh(target)
    return target


def delete_target(session: Session, group_id: int) -> bool:
    target = session.get(GroupTarget, group_id)
    if target is None:
        return False
    session.delete(target)
    session.commit()
    return True


def qualifies(activity: Activity, rules: TargetRules) -> bool:
    """Does this activity count as one exercise?

    Time is the universal fallback. A sport may add a distance threshold, in which case
    either one qualifying is enough — a short but long-distance run still counts.
    """
    minutes = (activity.moving_time or 0) / 60
    rule = rules.sports.get(activity.sport_type or "")

    if rule is None or (rule.min_minutes is None and rule.min_distance_km is None):
        return minutes >= rules.default_min_minutes

    if rule.min_minutes is not None and minutes >= rule.min_minutes:
        return True
    if rule.min_distance_km is not None and (activity.distance or 0) / 1000 >= rule.min_distance_km:
        return True
    return False


def period_bounds(period: str, now: datetime) -> tuple[datetime, datetime]:
    """Start (inclusive) and end (exclusive) of the period containing `now`, in UTC."""
    now = now.astimezone(UTC)
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if period == "week":
        # ISO weeks start on Monday.
        start = midnight - timedelta(days=now.weekday())
        return start, start + timedelta(days=7)

    if period == "month":
        start = midnight.replace(day=1)
        days_in_month = monthrange(start.year, start.month)[1]
        return start, start + timedelta(days=days_in_month)

    if period == "year":
        start = midnight.replace(month=1, day=1)
        return start, start.replace(year=start.year + 1)

    raise ValueError(f"unknown period {period!r}")


def _periods_remaining(period: str, period_end: datetime, until: datetime) -> int:
    """How many whole periods, including the current one, are left before `until`."""
    if until <= period_end:
        return 1 if until > datetime.now(UTC) else 0

    remaining = 1
    cursor = period_end
    # Bounded so a far-future `until` with weekly periods can't spin.
    while cursor < until and remaining < 1000:
        _, cursor = period_bounds(period, cursor)
        remaining += 1
    return remaining


def target_progress(session: Session, group: Group, now: datetime | None = None) -> TargetProgress:
    now = now or datetime.now(UTC)

    target = session.get(GroupTarget, group.id)
    if target is None:
        raise LookupError(f"group {group.id} has no target")

    rules = TargetRules.model_validate(target.rules)
    period_start, period_end = period_bounds(target.period, now)

    members = session.exec(
        select(Athlete)
        .join(GroupMembership, GroupMembership.athlete_id == Athlete.athlete_id)
        .where(GroupMembership.group_id == group.id)
        .order_by(GroupMembership.joined_at)
    ).all()

    completed: dict[int, int] = {athlete.athlete_id: 0 for athlete in members}
    if members:
        activities = session.exec(
            select(Activity).where(
                Activity.owner_id.in_(list(completed)),
                Activity.start_date >= period_start,
                Activity.start_date < period_end,
            )
        ).all()
        for activity in activities:
            # Qualification is evaluated in Python, not SQL: the rules are per-sport and
            # OR'd across thresholds, which would be an unreadable query for no gain at
            # this data size.
            if qualifies(activity, rules):
                completed[activity.owner_id] += 1

    progress = [
        MemberProgress(
            athlete_id=athlete.athlete_id,
            name=athlete.name,
            completed=completed[athlete.athlete_id],
            remaining=max(target.count - completed[athlete.athlete_id], 0),
            is_complete=completed[athlete.athlete_id] >= target.count,
            percent=round(min(completed[athlete.athlete_id] / target.count, 1.0) * 100, 1),
        )
        for athlete in members
    ]
    # Furthest ahead first.
    progress.sort(key=lambda member: member.completed, reverse=True)

    return TargetProgress(
        group_id=group.id,
        group_name=group.name,
        target=to_read(target),
        period_start=period_start,
        period_end=period_end,
        days_left_in_period=max((period_end - now).days, 0),
        periods_remaining=_periods_remaining(target.period, period_end, target.until),
        is_expired=now > target.until,
        members=progress,
    )
