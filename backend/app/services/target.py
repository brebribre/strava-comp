"""Group training targets: storage, qualification rules, and progress."""

from calendar import monthrange
from collections import defaultdict
from collections.abc import Iterable
from datetime import UTC, date, datetime, time, timedelta

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


def meets_rule(rules: TargetRules, sport: str | None, minutes: float, km: float) -> bool:
    """Does this much training, in this sport, clear the bar?

    Time is the universal fallback. A sport may add a distance threshold, in which case
    either one qualifying is enough — a short but long-distance run still counts.

    Deliberately takes bare numbers rather than an activity, because the same bar is
    applied twice: to one activity, and to a whole day of them added up.
    """
    rule = rules.sports.get(sport or "")

    if rule is None or (rule.min_minutes is None and rule.min_distance_km is None):
        return minutes >= rules.default_min_minutes

    if rule.min_minutes is not None and minutes >= rule.min_minutes:
        return True
    if rule.min_distance_km is not None and km >= rule.min_distance_km:
        return True
    return False


def time_bar(rules: TargetRules, sport: str | None) -> float:
    """The minutes this sport asks for, falling back to the default bar.

    Used when sports have to be compared on one scale, which only time offers.
    """
    rule = rules.sports.get(sport or "")
    if rule is not None and rule.min_minutes is not None:
        return rule.min_minutes
    return rules.default_min_minutes


def qualifies(activity: Activity, rules: TargetRules) -> bool:
    """Does this single activity count as one exercise on its own?"""
    return meets_rule(
        rules,
        activity.sport_type,
        (activity.moving_time or 0) / 60,
        (activity.distance or 0) / 1000,
    )


def local_start(activity: Activity) -> datetime:
    """The athlete's own wall clock for this activity, naive.

    Falls back to the UTC instant for rows written before we stored the local time —
    which is what the old counting did for everyone, so nothing regresses.
    """
    if activity.start_date_local is not None:
        return activity.start_date_local
    if activity.start_date is not None:
        return activity.start_date.astimezone(UTC).replace(tzinfo=None)
    return datetime.min


def activities_on_local_day(session: Session, owner_id: int, day: date) -> list[Activity]:
    """Everything this athlete did on this day, on their own clock.

    Queried a day either side in UTC and then narrowed on the local date, which is what
    makes it correct for someone whose day straddles UTC's.
    """
    window_start = datetime.combine(day, time.min, tzinfo=UTC) - timedelta(days=1)
    window_end = datetime.combine(day, time.max, tzinfo=UTC) + timedelta(days=1)

    nearby = session.exec(
        select(Activity).where(
            Activity.owner_id == owner_id,
            Activity.start_date >= window_start,
            Activity.start_date <= window_end,
        )
    ).all()
    return [item for item in nearby if local_start(item).date() == day]


def count_exercises(activities: Iterable[Activity], rules: TargetRules) -> int:
    """How many exercises this set of activities is worth.

    Three passes over each *local* day:

    1. Every activity that clears the bar on its own counts, exactly as before.
    2. Per sport, what is left over is added together and counts once more if that total
       clears the sport's bar. Splitting a run in two should not erase it.
    3. Whatever is still left, if it spans more than one sport, is added up by *time* and
       counts once if it clears the strictest bar of the sports involved. Half an hour of
       running and a short gym session is a day's training however it is labelled.

    Only leftovers are ever combined, so a real session is never merged into the scraps
    around it: a half-hour run plus two twelve-minute ones is two, not one. And because
    step 1 is untouched, this can only ever credit more than per-activity counting, never
    less — nobody loses a week they had already banked.

    Step 3 measures time alone, because distance cannot be added across sports: three
    kilometres of running and ten on a bike are not thirteen kilometres of anything. It
    takes the *strictest* bar rather than the most lenient, so mixing sports is never an
    easier way to hit a target than staying in one.
    """
    days: dict[date, list[Activity]] = defaultdict(list)
    for activity in activities:
        days[local_start(activity).date()].append(activity)

    total = 0
    for items in days.values():
        by_sport: dict[str, list[Activity]] = defaultdict(list)
        for item in items:
            if qualifies(item, rules):
                total += 1
            else:
                by_sport[item.sport_type or ""].append(item)

        remaining: dict[str, list[Activity]] = {}
        for sport, leftovers in by_sport.items():
            minutes = sum(item.moving_time or 0 for item in leftovers) / 60
            km = sum(item.distance or 0 for item in leftovers) / 1000
            if meets_rule(rules, sport, minutes, km):
                total += 1
            else:
                remaining[sport] = leftovers

        # Only a genuinely mixed day reaches this: a single sport has already been measured
        # against its own rule above, and re-measuring it here would just repeat that.
        if len(remaining) > 1:
            minutes = sum(
                item.moving_time or 0 for leftovers in remaining.values() for item in leftovers
            ) / 60
            if minutes >= max(time_bar(rules, sport) for sport in remaining):
                total += 1

    return total


def period_bounds(period: str, now: datetime) -> tuple[datetime, datetime]:
    """Start (inclusive) and end (exclusive) of the period containing `now`.

    Aware input is normalised to UTC and comes back aware; a naive input is treated as
    somebody's local wall clock and comes back naive, which is how per-member periods are
    built without inventing a timezone object per athlete.
    """
    if now.tzinfo is not None:
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


def started(activity: Activity, target: GroupTarget) -> bool:
    """Is this activity inside the target's window?

    The start date is compared as a *calendar date* on the athlete's own clock, not as an
    instant. A target starting "Aug 24" is picked from a date field and means the day, so
    for a brother in Tokyo it has to mean his Aug 24 — comparing instants would put UTC
    midnight nine hours into his morning and quietly drop the session he did before it.
    """
    if activity.start_date is None:
        return False
    return local_start(activity).date() >= target.starts_at.astimezone(UTC).date()


def _local_now(now: datetime, athlete: Athlete) -> datetime:
    """`now` on this athlete's wall clock, naive. No offset on record means UTC."""
    return now.astimezone(UTC).replace(tzinfo=None) + timedelta(seconds=athlete.utc_offset or 0)


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
        # Each member's period runs on their own clock, so the query fetches a window wide
        # enough to cover every timezone and the exact edges are cut per member below.
        activities = session.exec(
            select(Activity).where(
                Activity.owner_id.in_(list(completed)),
                Activity.start_date >= period_start - timedelta(days=1),
                Activity.start_date < period_end + timedelta(days=1),
            )
        ).all()

        by_owner: dict[int, list[Activity]] = defaultdict(list)
        for activity in activities:
            by_owner[activity.owner_id].append(activity)

        for athlete in members:
            local_start_bound, local_end_bound = period_bounds(
                target.period, _local_now(now, athlete)
            )
            mine = [
                activity
                for activity in by_owner.get(athlete.athlete_id, [])
                # A target that starts mid-period only counts from its start date, so
                # yesterday's session isn't credited to a target created today.
                if started(activity, target)
                and local_start_bound <= local_start(activity) < local_end_bound
            ]
            # Counting happens in Python, not SQL: the rules are per-sport, OR'd across
            # thresholds, and now aggregate per day, which no readable query would express.
            completed[athlete.athlete_id] = count_exercises(mine, rules)

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
        # A day either side, so an activity that is late Sunday in UTC but Monday locally
        # (or the reverse) still lands in the week its athlete lived through.
        activities = session.exec(
            select(Activity).where(
                Activity.owner_id.in_(member_ids),
                Activity.start_date >= earliest - timedelta(days=1),
                Activity.start_date < current_end + timedelta(days=1),
            )
        ).all()

    # Weeks are keyed by local calendar date: the athlete's own Monday, not UTC's. Bucketing
    # first and counting per bucket is what lets a day's activities add up.
    grouped: dict[tuple[int, date], list[Activity]] = defaultdict(list)
    for activity in activities:
        if not started(activity, target):
            continue
        local_week_start, _ = period_bounds("week", local_start(activity))
        grouped[(activity.owner_id, local_week_start.date())].append(activity)

    counts = {key: count_exercises(items, rules) for key, items in grouped.items()}

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
                        completed=(
                            done := counts.get((athlete.athlete_id, week_start.date()), 0)
                        ),
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
