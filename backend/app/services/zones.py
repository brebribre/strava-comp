"""Effort zones: bucketing runs by heart rate, and tracking pace within each bucket.

Chosen over workout-type categories because Strava's `workout_type` is almost never set,
and detecting intervals needs per-split data that only exists on enriched activities.
Pace at a *fixed* effort is also the cleanest measure of improvement.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func
from sqlmodel import Session, select

from app.models import Activity
from app.schemas.zones import ZoneBucket, ZoneMonthPoint, ZoneRecap

# Standard five-zone model as a percentage of maximum heart rate, with names runners use.
ZONE_DEFINITIONS: list[tuple[int, str, int, int]] = [
    (1, "Recovery", 0, 60),
    (2, "Easy", 60, 70),
    (3, "Steady", 70, 80),
    (4, "Threshold", 80, 90),
    (5, "Hard", 90, 200),
]

# A single sensor spike shouldn't define the top of every zone, so the estimate uses a high
# percentile of observed maxima rather than the outright maximum.
HR_MAX_PERCENTILE = 0.95
MIN_DISTANCE_FOR_PACE = 500  # metres; shorter efforts make pace meaningless


def estimate_hr_max(session: Session, athlete_id: int) -> tuple[int, str]:
    """Estimate maximum heart rate from the athlete's own history.

    Strava stores configured zones, but reading them needs `profile:read_all`, which this
    app deliberately doesn't request — so the estimate comes from observed data.
    """
    value = session.exec(
        select(
            func.percentile_disc(HR_MAX_PERCENTILE).within_group(Activity.max_heartrate.asc())
        ).where(Activity.owner_id == athlete_id, Activity.max_heartrate.is_not(None))
    ).one()

    if value:
        return int(value), "95th percentile of your recorded maximums"

    # Some devices report only an average. The hardest session's average sits well below a
    # true maximum, so scale it up rather than falling back to a generic number.
    highest_average = session.exec(
        select(func.max(Activity.average_heartrate)).where(
            Activity.owner_id == athlete_id, Activity.average_heartrate.is_not(None)
        )
    ).one()
    if highest_average:
        return round(highest_average / 0.92), "estimated from your hardest average — no maximums recorded"

    # No heart-rate data at all.
    return 190, "default estimate — no heart-rate data recorded"


def _zone_for(average_heartrate: float, hr_max: int) -> int | None:
    if not average_heartrate or hr_max <= 0:
        return None
    percentage = average_heartrate / hr_max * 100
    for zone, _, low, high in ZONE_DEFINITIONS:
        if low <= percentage < high:
            return zone
    return 5 if percentage >= 90 else 1


def _pace(distance: float, moving_time: int) -> float | None:
    if distance < MIN_DISTANCE_FOR_PACE or moving_time <= 0:
        return None
    return moving_time / (distance / 1000)


def _aggregate(activities: list[Activity], hr_max: int) -> dict[int, dict]:
    """Totals per zone. Pace is aggregate — total time over total distance."""
    buckets: dict[int, dict] = {}
    for activity in activities:
        zone = _zone_for(activity.average_heartrate or 0, hr_max)
        if zone is None:
            continue
        bucket = buckets.setdefault(
            zone, {"count": 0, "distance": 0.0, "moving_time": 0, "hr_sum": 0.0, "hr_n": 0}
        )
        bucket["count"] += 1
        bucket["distance"] += activity.distance or 0
        bucket["moving_time"] += activity.moving_time or 0
        if activity.average_heartrate:
            bucket["hr_sum"] += activity.average_heartrate
            bucket["hr_n"] += 1
    return buckets


def zone_recap(session: Session, athlete_id: int, sport: str, months: int) -> ZoneRecap:
    until = datetime.now(UTC)
    since = until - timedelta(days=months * 30)
    previous_since = since - timedelta(days=months * 30)

    hr_max, basis = estimate_hr_max(session, athlete_id)

    def load(start: datetime, end: datetime) -> list[Activity]:
        return session.exec(
            select(Activity).where(
                Activity.owner_id == athlete_id,
                Activity.sport_type == sport,
                Activity.start_date >= start,
                Activity.start_date < end,
            )
        ).all()

    current = load(since, until)
    previous = load(previous_since, since)

    current_buckets = _aggregate(current, hr_max)
    previous_buckets = _aggregate(previous, hr_max)

    zones: list[ZoneBucket] = []
    for zone, label, low, high in ZONE_DEFINITIONS:
        bucket = current_buckets.get(zone)
        earlier = previous_buckets.get(zone)
        if not bucket:
            continue

        pace = _pace(bucket["distance"], bucket["moving_time"])
        previous_pace = _pace(earlier["distance"], earlier["moving_time"]) if earlier else None

        zones.append(
            ZoneBucket(
                zone=zone,
                label=label,
                low_pct=low,
                high_pct=min(high, 100),
                low_bpm=round(hr_max * low / 100),
                high_bpm=round(hr_max * min(high, 100) / 100),
                activity_count=bucket["count"],
                distance=bucket["distance"],
                moving_time=bucket["moving_time"],
                avg_heartrate=round(bucket["hr_sum"] / bucket["hr_n"], 1) if bucket["hr_n"] else None,
                avg_pace_seconds_per_km=round(pace, 1) if pace else None,
                previous_activity_count=earlier["count"] if earlier else 0,
                previous_avg_pace_seconds_per_km=round(previous_pace, 1) if previous_pace else None,
                pace_delta_seconds=(
                    round(pace - previous_pace, 1) if pace and previous_pace else None
                ),
            )
        )

    # Monthly pace per zone, for the trend chart.
    monthly: dict[tuple[datetime, int], dict] = {}
    for activity in current:
        zone = _zone_for(activity.average_heartrate or 0, hr_max)
        if zone is None or not activity.start_date:
            continue
        key = (activity.start_date.replace(day=1).date(), zone)
        point = monthly.setdefault(key, {"count": 0, "distance": 0.0, "moving_time": 0})
        point["count"] += 1
        point["distance"] += activity.distance or 0
        point["moving_time"] += activity.moving_time or 0

    months_out = [
        ZoneMonthPoint(
            month=month,
            zone=zone,
            activity_count=values["count"],
            avg_pace_seconds_per_km=(
                round(p, 1) if (p := _pace(values["distance"], values["moving_time"])) else None
            ),
        )
        for (month, zone), values in sorted(monthly.items())
    ]

    classified = sum(z.activity_count for z in zones)
    return ZoneRecap(
        sport_type=sport,
        since=since,
        until=until,
        hr_max=hr_max,
        hr_max_basis=basis,
        zones=zones,
        months=months_out,
        classified_count=classified,
        unclassified_count=len(current) - classified,
    )
