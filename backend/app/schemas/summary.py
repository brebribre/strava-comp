from datetime import datetime

from pydantic import BaseModel


class SportSummary(BaseModel):
    sport_type: str
    activity_count: int
    total_distance: float       # metres
    total_moving_time: int      # seconds
    total_elevation_gain: float  # metres
    avg_heartrate: float | None


class MemberSummary(BaseModel):
    """One group member's totals for the window.

    Members with no activities are included with zeroes — a leaderboard that silently
    drops inactive people is misleading.
    """

    athlete_id: int
    name: str
    activity_count: int
    total_distance: float
    total_moving_time: int
    total_elevation_gain: float
    avg_heartrate: float | None
    by_sport: list[SportSummary]


class GroupSummary(BaseModel):
    group_id: int
    group_name: str
    since: datetime
    until: datetime
    members: list[MemberSummary]


class TrendPoint(BaseModel):
    week_start: datetime
    activity_count: int
    total_distance: float
    total_moving_time: int


class MemberTrend(BaseModel):
    athlete_id: int
    name: str
    weeks: list[TrendPoint]


class GroupTrend(BaseModel):
    group_id: int
    group_name: str
    since: datetime
    until: datetime
    members: list[MemberTrend]
