from datetime import date, datetime

from pydantic import BaseModel


class SportTotals(BaseModel):
    activity_count: int
    distance: float          # metres
    moving_time: int         # seconds
    elevation: float         # metres
    avg_heartrate: float | None


class SportOverview(BaseModel):
    """One sport in the period, next to the equivalent previous period."""

    sport_type: str
    current: SportTotals
    previous: SportTotals
    # Percentage change per metric; null when the previous period was empty, because
    # "up from zero" is not a meaningful percentage.
    growth_activity_count: float | None
    growth_distance: float | None
    growth_moving_time: float | None

    first_seen: datetime
    last_seen: datetime


class RecapOverview(BaseModel):
    since: datetime
    until: datetime
    days: int
    total: SportTotals
    previous_total: SportTotals
    sports: list[SportOverview]

    # False when the comparison window starts before there is any recorded history, which
    # makes "growth" measure when tracking began rather than any change in training.
    baseline_complete: bool
    first_activity: datetime | None


class MonthPoint(BaseModel):
    month: date              # first day of the month
    activity_count: int
    distance: float
    moving_time: int
    elevation: float
    avg_heartrate: float | None
    # Foot sports report pace, wheeled sports speed; null where neither applies.
    avg_pace_seconds_per_km: float | None
    avg_speed_kmh: float | None


class BestEffort(BaseModel):
    label: str
    value: str
    activity_id: int
    activity_name: str | None
    start_date: datetime


class Consistency(BaseModel):
    active_weeks: int
    total_weeks: int
    longest_streak_weeks: int
    avg_per_week: float
    longest_gap_days: int


class SportRecap(BaseModel):
    sport_type: str
    since: datetime
    until: datetime
    totals: SportTotals
    months: list[MonthPoint]
    bests: list[BestEffort]
    consistency: Consistency
