"""Personal, per-sport recap: how each sport has grown over time.

Unlike the group summary this is single-athlete and long-range, so it works in months
rather than days and always compares against the preceding period.
"""

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func
from sqlmodel import Session, select

from app.models import Activity
from app.schemas.recap import (
    BestEffort,
    Consistency,
    MonthPoint,
    RecapOverview,
    SportOverview,
    SportRecap,
    SportTotals,
)

FOOT_SPORTS = {"Run", "TrailRun", "VirtualRun", "Walk", "Hike"}
WHEEL_SPORTS = {"Ride", "VirtualRide", "GravelRide", "MountainBikeRide", "EBikeRide"}

EMPTY = SportTotals(activity_count=0, distance=0.0, moving_time=0, elevation=0.0, avg_heartrate=None)


def _growth(current: float, previous: float) -> float | None:
    """Percentage change, or None when there's no baseline to compare against."""
    if previous <= 0:
        return None
    return round((current - previous) / previous * 100, 1)


def _totals_query(athlete_id: int, since: datetime, until: datetime, by_sport: bool):
    columns = [
        func.count().label("activity_count"),
        func.coalesce(func.sum(Activity.distance), 0.0).label("distance"),
        func.coalesce(func.sum(Activity.moving_time), 0).label("moving_time"),
        func.coalesce(func.sum(Activity.total_elevation_gain), 0.0).label("elevation"),
        func.avg(Activity.average_heartrate).label("avg_heartrate"),
    ]
    if by_sport:
        columns = [
            Activity.sport_type,
            *columns,
            func.min(Activity.start_date).label("first_seen"),
            func.max(Activity.start_date).label("last_seen"),
        ]

    statement = select(*columns).where(
        Activity.owner_id == athlete_id,
        Activity.start_date >= since,
        Activity.start_date < until,
    )
    if by_sport:
        statement = statement.group_by(Activity.sport_type)
    return statement


def _to_totals(row) -> SportTotals:
    return SportTotals(
        activity_count=row.activity_count,
        distance=float(row.distance or 0),
        moving_time=int(row.moving_time or 0),
        elevation=float(row.elevation or 0),
        avg_heartrate=round(float(row.avg_heartrate), 1) if row.avg_heartrate else None,
    )


def overview(session: Session, athlete_id: int, days: int) -> RecapOverview:
    """Every sport in the window, each next to its own previous-period baseline."""
    until = datetime.now(UTC)
    since = until - timedelta(days=days)
    # The comparison window is the same length, immediately before.
    previous_since = since - timedelta(days=days)

    # Growth is only meaningful if the comparison window is actually covered by data. A
    # previous period that predates the athlete's first activity would report enormous
    # percentages that really only say "this is when I started tracking".
    first_activity = session.exec(
        select(func.min(Activity.start_date)).where(Activity.owner_id == athlete_id)
    ).one()
    baseline_complete = first_activity is not None and first_activity <= previous_since

    total_row = session.exec(_totals_query(athlete_id, since, until, by_sport=False)).one()
    previous_total_row = session.exec(
        _totals_query(athlete_id, previous_since, since, by_sport=False)
    ).one()

    current_rows = session.exec(_totals_query(athlete_id, since, until, by_sport=True)).all()
    previous_rows = {
        row.sport_type: row
        for row in session.exec(_totals_query(athlete_id, previous_since, since, by_sport=True)).all()
    }

    sports: list[SportOverview] = []
    for row in current_rows:
        current = _to_totals(row)
        previous_row = previous_rows.get(row.sport_type)
        previous = _to_totals(previous_row) if previous_row else EMPTY
        sports.append(
            SportOverview(
                sport_type=row.sport_type or "Unknown",
                current=current,
                previous=previous,
                growth_activity_count=(
                    _growth(current.activity_count, previous.activity_count)
                    if baseline_complete
                    else None
                ),
                growth_distance=(
                    _growth(current.distance, previous.distance) if baseline_complete else None
                ),
                growth_moving_time=(
                    _growth(current.moving_time, previous.moving_time) if baseline_complete else None
                ),
                first_seen=row.first_seen,
                last_seen=row.last_seen,
            )
        )

    # Most time invested first — that ranks a sport by commitment rather than by distance,
    # which would always put running on top.
    sports.sort(key=lambda s: s.current.moving_time, reverse=True)

    return RecapOverview(
        since=since,
        until=until,
        days=days,
        total=_to_totals(total_row),
        previous_total=_to_totals(previous_total_row),
        sports=sports,
        baseline_complete=baseline_complete,
        first_activity=first_activity,
    )


def _month_points(session: Session, athlete_id: int, sport: str, since: datetime, until: datetime) -> list[MonthPoint]:
    month = func.date_trunc("month", Activity.start_date).label("month")
    rows = session.exec(
        select(
            month,
            func.count().label("activity_count"),
            func.coalesce(func.sum(Activity.distance), 0.0).label("distance"),
            func.coalesce(func.sum(Activity.moving_time), 0).label("moving_time"),
            func.coalesce(func.sum(Activity.total_elevation_gain), 0.0).label("elevation"),
            func.avg(Activity.average_heartrate).label("avg_heartrate"),
        )
        .where(
            Activity.owner_id == athlete_id,
            Activity.sport_type == sport,
            Activity.start_date >= since,
            Activity.start_date < until,
        )
        .group_by(month)
        .order_by(month)
    ).all()

    points: list[MonthPoint] = []
    for row in rows:
        distance = float(row.distance or 0)
        moving_time = int(row.moving_time or 0)
        pace = speed = None
        # Pace and speed are aggregate: total time over total distance for the month, which
        # weights long sessions properly rather than averaging per-activity rates.
        if distance > 100 and moving_time > 0:
            if sport in FOOT_SPORTS:
                pace = round(moving_time / (distance / 1000), 1)
            elif sport in WHEEL_SPORTS:
                speed = round(distance / 1000 / (moving_time / 3600), 2)

        points.append(
            MonthPoint(
                month=row.month.date().replace(day=1),
                activity_count=row.activity_count,
                distance=distance,
                moving_time=moving_time,
                elevation=float(row.elevation or 0),
                avg_heartrate=round(float(row.avg_heartrate), 1) if row.avg_heartrate else None,
                avg_pace_seconds_per_km=pace,
                avg_speed_kmh=speed,
            )
        )
    return points


def _format_pace(seconds_per_km: float) -> str:
    # Round first, then split: rounding the seconds separately yields "6:60/km".
    total = round(seconds_per_km)
    return f"{total // 60}:{total % 60:02d} /km"


def _bests(session: Session, athlete_id: int, sport: str, since: datetime, until: datetime) -> list[BestEffort]:
    activities = session.exec(
        select(Activity).where(
            Activity.owner_id == athlete_id,
            Activity.sport_type == sport,
            Activity.start_date >= since,
            Activity.start_date < until,
        )
    ).all()
    if not activities:
        return []

    bests: list[BestEffort] = []

    def add(label: str, activity: Activity, value: str) -> None:
        bests.append(
            BestEffort(
                label=label,
                value=value,
                activity_id=activity.id,
                activity_name=activity.name,
                start_date=activity.start_date,
            )
        )

    with_distance = [a for a in activities if (a.distance or 0) > 0]
    if with_distance:
        longest = max(with_distance, key=lambda a: a.distance or 0)
        add("Longest distance", longest, f"{(longest.distance or 0) / 1000:.1f} km")

    longest_time = max(activities, key=lambda a: a.moving_time or 0)
    if longest_time.moving_time:
        hours, minutes = divmod(round(longest_time.moving_time / 60), 60)
        add("Longest session", longest_time, f"{hours}h {minutes}m" if hours else f"{minutes}m")

    # A fastest pace over a trivial distance is noise, so require a real effort.
    pace_candidates = [
        a for a in with_distance if (a.distance or 0) >= 1000 and (a.moving_time or 0) > 0
    ]
    if pace_candidates and sport in FOOT_SPORTS:
        fastest = min(pace_candidates, key=lambda a: a.moving_time / (a.distance / 1000))
        add("Fastest pace", fastest, _format_pace(fastest.moving_time / (fastest.distance / 1000)))
    elif pace_candidates and sport in WHEEL_SPORTS:
        fastest = max(pace_candidates, key=lambda a: a.distance / a.moving_time)
        add("Fastest average", fastest, f"{fastest.distance / 1000 / (fastest.moving_time / 3600):.1f} km/h")

    climbers = [a for a in activities if (a.total_elevation_gain or 0) > 0]
    if climbers:
        climb = max(climbers, key=lambda a: a.total_elevation_gain or 0)
        add("Most elevation", climb, f"{round(climb.total_elevation_gain or 0)} m")

    # Strava's "relative effort" — a better proxy for hardest session than raw duration.
    efforts = [(a, (a.raw_data or {}).get("suffer_score")) for a in activities]
    efforts = [(a, score) for a, score in efforts if isinstance(score, (int, float))]
    if efforts:
        activity, score = max(efforts, key=lambda pair: pair[1])
        add("Hardest effort", activity, f"{round(score)} relative effort")

    return bests


def _consistency(activities_dates: list[datetime], since: datetime, until: datetime) -> Consistency:
    total_weeks = max(round((until - since).days / 7), 1)
    if not activities_dates:
        return Consistency(
            active_weeks=0, total_weeks=total_weeks, longest_streak_weeks=0,
            avg_per_week=0.0, longest_gap_days=(until - since).days,
        )

    weeks = sorted({(d.isocalendar().year, d.isocalendar().week) for d in activities_dates})
    longest = current = 1
    for previous, nxt in zip(weeks, weeks[1:]):
        # Consecutive if it's the next week number, or the first week of the next year.
        consecutive = (nxt[0] == previous[0] and nxt[1] == previous[1] + 1) or (
            nxt[0] == previous[0] + 1 and nxt[1] == 1
        )
        current = current + 1 if consecutive else 1
        longest = max(longest, current)

    ordered = sorted(activities_dates)
    gaps = [(b - a).days for a, b in zip(ordered, ordered[1:])] or [0]

    return Consistency(
        active_weeks=len(weeks),
        total_weeks=total_weeks,
        longest_streak_weeks=longest,
        avg_per_week=round(len(activities_dates) / total_weeks, 1),
        longest_gap_days=max(gaps),
    )


def sport_recap(session: Session, athlete_id: int, sport: str, months: int) -> SportRecap:
    until = datetime.now(UTC)
    since = until - timedelta(days=months * 30)

    totals_row = session.exec(
        _totals_query(athlete_id, since, until, by_sport=True).where(Activity.sport_type == sport)
    ).first()

    dates = session.exec(
        select(Activity.start_date).where(
            Activity.owner_id == athlete_id,
            Activity.sport_type == sport,
            Activity.start_date >= since,
            Activity.start_date < until,
        )
    ).all()

    return SportRecap(
        sport_type=sport,
        since=since,
        until=until,
        totals=_to_totals(totals_row) if totals_row else EMPTY,
        months=_month_points(session, athlete_id, sport, since, until),
        bests=_bests(session, athlete_id, sport, since, until),
        consistency=_consistency([d for d in dates if d], since, until),
    )
