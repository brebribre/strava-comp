from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

Period = Literal["week", "month", "year"]


class SportRule(BaseModel):
    """What qualifies as an exercise for one sport.

    When both thresholds are set they are OR'd — a run counts if it was long enough in
    *time* or far enough in *distance*. A sport with neither falls back to the default.
    """

    min_minutes: int | None = Field(default=None, ge=1, le=1440)
    min_distance_km: float | None = Field(default=None, gt=0, le=1000)


class TargetRules(BaseModel):
    # Any sport without its own rule qualifies on time alone.
    default_min_minutes: int = Field(default=30, ge=1, le=1440)
    sports: dict[str, SportRule] = Field(default_factory=dict)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "default_min_minutes": 30,
                    "sports": {
                        "Run": {"min_minutes": 20, "min_distance_km": 3},
                        "Tennis": {"min_minutes": 45},
                        "WeightTraining": {"min_minutes": 30},
                    },
                }
            ]
        }
    }


class TargetWrite(BaseModel):
    count: int = Field(ge=1, le=100, description="How many qualifying exercises per period.")
    period: Period
    starts_at: datetime | None = Field(
        default=None, description="When the target begins. Defaults to now."
    )
    until: datetime = Field(description="The target stops applying after this date.")
    rules: TargetRules = Field(default_factory=TargetRules)

    @model_validator(mode="after")
    def _window_is_forwards(self) -> "TargetWrite":
        if self.starts_at is not None and self.until <= self.starts_at:
            raise ValueError("until must be after starts_at")
        return self


class TargetRead(TargetWrite):
    group_id: int
    # Always resolved on read, even when the write left it to default.
    starts_at: datetime
    created_at: datetime
    updated_at: datetime


class MemberProgress(BaseModel):
    athlete_id: int
    name: str
    completed: int
    remaining: int
    is_complete: bool
    percent: float


class TargetProgress(BaseModel):
    group_id: int
    group_name: str
    target: TargetRead
    period_start: datetime
    period_end: datetime
    days_left_in_period: int
    periods_remaining: int
    is_expired: bool
    # The target's start date is still in the future — nothing counts yet.
    is_pending: bool
    members: list[MemberProgress]


class WeekMemberProgress(BaseModel):
    athlete_id: int
    name: str
    completed: int
    remaining: int
    is_complete: bool
    percent: float


class TargetWeek(BaseModel):
    """One past week, with every member's count against the target."""

    week_start: datetime
    week_end: datetime
    is_current: bool
    # False for weeks outside the target's [starts_at, until] window. Those weeks are not
    # failures — the target simply wasn't running yet (or had already ended).
    in_scope: bool
    target_count: int
    members: list[WeekMemberProgress]


class TargetHistory(BaseModel):
    group_id: int
    group_name: str
    target_count: int
    period: Period
    weeks: list[TargetWeek]
