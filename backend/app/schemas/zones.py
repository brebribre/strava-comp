from datetime import date, datetime

from pydantic import BaseModel


class ZoneBucket(BaseModel):
    """One effort zone over the window, beside the equivalent previous period."""

    zone: int
    label: str
    low_pct: int
    high_pct: int
    low_bpm: int
    high_bpm: int

    activity_count: int
    distance: float
    moving_time: int
    avg_heartrate: float | None
    avg_pace_seconds_per_km: float | None

    previous_activity_count: int
    previous_avg_pace_seconds_per_km: float | None
    # Negative is an improvement: fewer seconds per kilometre at the same effort.
    pace_delta_seconds: float | None


class ZoneMonthPoint(BaseModel):
    month: date
    zone: int
    activity_count: int
    avg_pace_seconds_per_km: float | None


class ZoneRecap(BaseModel):
    sport_type: str
    since: datetime
    until: datetime

    # Estimated, because Strava's configured zones need a scope this app doesn't request.
    hr_max: int
    hr_max_basis: str

    zones: list[ZoneBucket]
    months: list[ZoneMonthPoint]
    classified_count: int
    unclassified_count: int
