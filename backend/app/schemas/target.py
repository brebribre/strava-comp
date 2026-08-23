from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

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
    until: datetime = Field(description="The target stops applying after this date.")
    rules: TargetRules = Field(default_factory=TargetRules)


class TargetRead(TargetWrite):
    group_id: int
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
    members: list[MemberProgress]
