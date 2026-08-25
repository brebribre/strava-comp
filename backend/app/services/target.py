"""Group training targets: storage, qualification rules, and progress."""

from calendar import monthrange
from datetime import UTC, datetime, timedelta

from sqlmodel import Session, select

from app.models import Activity, Athlete, Group, GroupMembership, GroupTarget
from app.models.base import utcnow
from app.schemas.target import (
    MemberProgress,
    TargetHistory,
    TargetProgress,
    TargetRead,
    TargetRules,
    TargetWeek,
    TargetWrite,
    WeekMemberProgress,
)
from app.services.errors import GroupNotFound


def get_target(session: Session, group_id: int) -> GroupTarget | None:
    return session.get(GroupTarget, group_id)


def to_read(target: GroupTarget) -> TargetRead:
    return TargetRead(
        group_id=target.group_id,
        count=target.count,
        period=target.period,
        starts_at=target.starts_at,
        until=target.until,
        rules=TargetRules.model_validate(target.rules),
        created_at=target.created_at,
        updated_at=target.updated_at,
    )


def upsert_target(session: Session, group_id: int, data: TargetWrite) -> GroupTarget:
    """Create or replace the group's target. One target per group, so this is a replace."""
    if session.get(Group, group_id) is None:
        raise GroupNotFound(f"no group {group_id}")

    # An omitted start date means "this period" rather than "this instant" — a weekly target
    # set on Wednesday should still credit Monday's session.
    starts_at = data.starts_at or period_bounds(data.period, utcnow())[0]

    target = session.get(GroupTarget, group_id)
    if target is None:
        target = GroupTarget(
            group_id=group_id,
            count=data.count,
            period=data.period,
            starts_at=starts_at,
            until=data.until,
            rules=data.rules.model_dump(),
        )
    else:
        target.count = data.count
        target.period = data.period
        target.starts_at = starts_at
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
    # A target that starts mid-period only counts activities from its start date, so
    # yesterday's session doesn't get credited to a target created today.
    count_from = max(period_start, target.starts_at)

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
                Activity.start_date >= count_from,
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
        is_pending=now < target.starts_at,
        members=progress,
    )


def target_history(
    session: Session, group: Group, weeks: int = 12, now: datetime | None = None
) -> TargetHistory:
    """Week-by-week counts for every member, newest first.

    Always weekly, even when the target period is a month or a year: a week is the unit
    people actually plan around, and a monthly target still reads sensibly as a weekly bar.
    """
    now = now or datetime.now(UTC)

    target = session.get(GroupTarget, group.id)
    if target is None:
        raise LookupError(f"group {group.id} has no target")

    rules = TargetRules.model_validate(target.rules)
    # A monthly or yearly target is spread across the weeks it covers, so the bar means
    # "on pace" rather than "hit the whole target this week".
    per_week = {
        "week": target.count,
        "month": max(round(target.count / 4.345), 1),
        "year": max(round(target.count / 52), 1),
    }[target.period]

    members = session.exec(
        select(Athlete)
        .join(GroupMembership, GroupMembership.athlete_id == Athlete.athlete_id)
        .where(GroupMembership.group_id == group.id)
        .order_by(GroupMembership.joined_at)
    ).all()
    member_ids = [athlete.athlete_id for athlete in members]

    current_start, current_end = period_bounds("week", now)
    earliest = current_start - timedelta(weeks=weeks - 1)

    activities = []
    if member_ids:
        activities = session.exec(
            select(Activity).where(
                Activity.owner_id.in_(member_ids),
                Activity.start_date >= earliest,
                Activity.start_date < current_end,
            )
        ).all()

    # (athlete, week_start) -> qualifying count
    counts: dict[tuple[int, datetime], int] = {}
    for activity in activities:
        if not qualifies(activity, rules):
            continue
        week_start, _ = period_bounds("week", activity.start_date)
        key = (activity.owner_id, week_start)
        counts[key] = counts.get(key, 0) + 1

    out: list[TargetWeek] = []
    for index in range(weeks):
        week_start = current_start - timedelta(weeks=index)
        week_end = week_start + timedelta(days=7)
        out.append(
            TargetWeek(
                week_start=week_start,
                week_end=week_end,
                is_current=index == 0,
                # The week counts only if it overlaps the target's window at all.
                in_scope=week_end > target.starts_at and week_start < target.until,
                target_count=per_week,
                members=[
                    WeekMemberProgress(
                        athlete_id=athlete.athlete_id,
                        name=athlete.name,
                        completed=(done := counts.get((athlete.athlete_id, week_start), 0)),
                        remaining=max(per_week - done, 0),
                        is_complete=done >= per_week,
                        percent=round(min(done / per_week, 1.0) * 100, 1),
                    )
                    for athlete in members
                ],
            )
        )

    return TargetHistory(
        group_id=group.id,
        group_name=group.name,
        target_count=per_week,
        period=target.period,
        weeks=out,
    )
