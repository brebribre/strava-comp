"""Group-level aggregation of member activity."""

from collections import defaultdict
from datetime import UTC, datetime, timedelta

from sqlalchemy import func
from sqlmodel import Session, select

from app.models import Activity, Athlete, Group, GroupMembership
from app.schemas.feed import FeedItem, GroupFeed
from app.services.activity_detail import primary_photo
from app.services.workout import parse_exercises
from app.schemas.summary import (
    GroupSummary,
    GroupTrend,
    MemberSummary,
    MemberTrend,
    SportBucket,
    SportSummary,
    TrendPoint,
)


def _summary_polyline(raw_data: dict | None) -> str | None:
    activity_map = (raw_data or {}).get("map") or {}
    return activity_map.get("summary_polyline") or activity_map.get("polyline") or None


def _window(days: int) -> tuple[datetime, datetime]:
    until = datetime.now(UTC)
    return until - timedelta(days=days), until


def _members(session: Session, group_id: int) -> list[Athlete]:
    return session.exec(
        select(Athlete)
        .join(GroupMembership, GroupMembership.athlete_id == Athlete.athlete_id)
        .where(GroupMembership.group_id == group_id)
        .order_by(GroupMembership.joined_at)
    ).all()


def group_summary(session: Session, group: Group, days: int) -> GroupSummary:
    """Per-member, per-sport totals for the window.

    Members are listed from the membership table rather than from the activity rows,
    so someone who did nothing this week still appears — with zeroes.
    """
    since, until = _window(days)
    members = _members(session, group.id)
    member_ids = [athlete.athlete_id for athlete in members]

    rows = []
    if member_ids:
        rows = session.exec(
            select(
                Activity.owner_id,
                Activity.sport_type,
                func.count().label("activity_count"),
                func.coalesce(func.sum(Activity.distance), 0.0).label("total_distance"),
                func.coalesce(func.sum(Activity.moving_time), 0).label("total_moving_time"),
                func.coalesce(func.sum(Activity.total_elevation_gain), 0.0).label("total_elevation"),
                func.avg(Activity.average_heartrate).label("avg_heartrate"),
            )
            .where(
                Activity.owner_id.in_(member_ids),
                Activity.start_date >= since,
                Activity.start_date <= until,
            )
            .group_by(Activity.owner_id, Activity.sport_type)
            .order_by(Activity.owner_id, Activity.sport_type)
        ).all()

    by_athlete: dict[int, list[SportSummary]] = defaultdict(list)
    for owner_id, sport_type, count, distance, moving_time, elevation, avg_hr in rows:
        by_athlete[owner_id].append(
            SportSummary(
                sport_type=sport_type or "Unknown",
                activity_count=count,
                total_distance=float(distance),
                total_moving_time=int(moving_time),
                total_elevation_gain=float(elevation),
                avg_heartrate=float(avg_hr) if avg_hr is not None else None,
            )
        )

    summaries = []
    for athlete in members:
        sports = by_athlete.get(athlete.athlete_id, [])
        # Overall average HR is weighted by activity count, so a long ride and a short
        # run don't count equally just because they're separate sports.
        hr_sports = [s for s in sports if s.avg_heartrate is not None]
        total_hr_activities = sum(s.activity_count for s in hr_sports)
        avg_hr = (
            sum(s.avg_heartrate * s.activity_count for s in hr_sports) / total_hr_activities
            if total_hr_activities
            else None
        )
        summaries.append(
            MemberSummary(
                athlete_id=athlete.athlete_id,
                name=athlete.name,
                activity_count=sum(s.activity_count for s in sports),
                total_distance=sum(s.total_distance for s in sports),
                total_moving_time=sum(s.total_moving_time for s in sports),
                total_elevation_gain=sum(s.total_elevation_gain for s in sports),
                avg_heartrate=round(avg_hr, 1) if avg_hr is not None else None,
                by_sport=sports,
            )
        )

    # Most active first — this is the comparison the group actually cares about.
    summaries.sort(key=lambda m: (m.total_moving_time, m.activity_count), reverse=True)

    return GroupSummary(
        group_id=group.id, group_name=group.name, since=since, until=until, members=summaries
    )


def group_trend(session: Session, group: Group, days: int) -> GroupTrend:
    """Weekly buckets per member, for a comparison chart."""
    since, until = _window(days)
    members = _members(session, group.id)
    member_ids = [athlete.athlete_id for athlete in members]

    rows = []
    if member_ids:
        week = func.date_trunc("week", Activity.start_date).label("week_start")
        # Grouped by sport as well as week, so the chart can stack by activity type.
        rows = session.exec(
            select(
                Activity.owner_id,
                week,
                Activity.sport_type,
                func.count().label("activity_count"),
                func.coalesce(func.sum(Activity.distance), 0.0).label("total_distance"),
                func.coalesce(func.sum(Activity.moving_time), 0).label("total_moving_time"),
            )
            .where(
                Activity.owner_id.in_(member_ids),
                Activity.start_date >= since,
                Activity.start_date <= until,
            )
            .group_by(Activity.owner_id, week, Activity.sport_type)
            .order_by(Activity.owner_id, week)
        ).all()

    # (athlete, week) -> the week's totals plus its per-sport slices.
    weeks: dict[tuple[int, datetime], TrendPoint] = {}
    for owner_id, week_start, sport_type, count, distance, moving_time in rows:
        point = weeks.get((owner_id, week_start))
        if point is None:
            point = TrendPoint(
                week_start=week_start,
                activity_count=0,
                total_distance=0.0,
                total_moving_time=0,
                by_sport=[],
            )
            weeks[(owner_id, week_start)] = point

        point.activity_count += count
        point.total_distance += float(distance)
        point.total_moving_time += int(moving_time)
        point.by_sport.append(
            SportBucket(
                sport_type=sport_type or "Unknown",
                activity_count=count,
                total_distance=float(distance),
                total_moving_time=int(moving_time),
            )
        )

    by_athlete: dict[int, list[TrendPoint]] = defaultdict(list)
    for (owner_id, _), point in sorted(weeks.items(), key=lambda item: item[0][1]):
        by_athlete[owner_id].append(point)

    return GroupTrend(
        group_id=group.id,
        group_name=group.name,
        since=since,
        until=until,
        members=[
            MemberTrend(
                athlete_id=a.athlete_id, name=a.name, weeks=by_athlete.get(a.athlete_id, [])
            )
            for a in members
        ],
    )


def group_feed(
    session: Session, group: Group, limit: int = 30, before: datetime | None = None
) -> GroupFeed:
    """Every member's activities, newest first — the group's shared timeline.

    Paginated by `before` (an activity start_date) rather than by offset, so activities
    arriving mid-scroll can't shift page boundaries and duplicate or skip rows.
    """
    members = {a.athlete_id: a.name for a in _members(session, group.id)}
    if not members:
        return GroupFeed(group_id=group.id, group_name=group.name, items=[], next_before=None)

    statement = (
        select(Activity)
        .where(Activity.owner_id.in_(list(members)), Activity.start_date.is_not(None))
        .order_by(Activity.start_date.desc(), Activity.id.desc())
        # One extra row tells us whether another page exists, without a second COUNT query.
        .limit(limit + 1)
    )
    if before is not None:
        statement = statement.where(Activity.start_date < before)

    rows = session.exec(statement).all()
    has_more = len(rows) > limit
    rows = rows[:limit]

    items = [
        FeedItem(
            activity_id=activity.id,
            athlete_id=activity.owner_id,
            athlete_name=members.get(activity.owner_id, "Unknown"),
            name=activity.name,
            sport_type=activity.sport_type,
            distance=activity.distance or 0.0,
            moving_time=activity.moving_time or 0,
            elapsed_time=activity.elapsed_time or 0,
            total_elevation_gain=activity.total_elevation_gain or 0.0,
            average_heartrate=activity.average_heartrate,
            start_date=activity.start_date,
            # summary_polyline, not the full one: the feed draws a thumbnail, and the
            # detailed polyline is several times larger per activity.
            polyline=_summary_polyline(activity.raw_data),
            photo_url=primary_photo(activity.raw_data),
            # Only present once an activity has been enriched: the list endpoint Strava
            # backfills from carries no description at all.
            exercises=parse_exercises((activity.raw_data or {}).get("description")),
        )
        for activity in rows
    ]

    return GroupFeed(
        group_id=group.id,
        group_name=group.name,
        items=items,
        next_before=items[-1].start_date if has_more and items else None,
    )
