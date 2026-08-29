from datetime import datetime

from pydantic import BaseModel

from app.schemas.workout import Exercise


class Split(BaseModel):
    split: int
    distance: float
    moving_time: int
    elevation_difference: float | None
    average_heartrate: float | None


class ActivityDetail(BaseModel):
    """One activity in full, as shown on its own page.

    Enriched from Strava's detailed endpoint, which carries fields the list endpoint
    omits: description, calories, splits, and the full-resolution GPS polyline.
    """

    activity_id: int
    athlete_id: int
    athlete_name: str

    name: str | None
    description: str | None
    sport_type: str | None
    start_date: datetime

    distance: float
    moving_time: int
    elapsed_time: int
    total_elevation_gain: float
    average_heartrate: float | None
    max_heartrate: float | None
    calories: float | None
    device_name: str | None

    # Google-encoded polyline; null for indoor activities with no GPS.
    polyline: str | None
    photo_url: str | None
    splits: list[Split]
    # Strength sessions logged in Hevy, Strong and the like write their sets into the
    # description; this is that, read back into a sequence. Empty for everything else.
    exercises: list[Exercise]

    # False when Strava couldn't be reached, so the page can say the detail is partial.
    is_detailed: bool
