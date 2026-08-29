from datetime import datetime

from pydantic import BaseModel

from app.schemas.workout import Exercise


class FeedItem(BaseModel):
    """One activity by one group member, as it appears in the feed."""

    activity_id: int
    athlete_id: int
    athlete_name: str
    name: str | None
    sport_type: str | None
    distance: float
    moving_time: int
    elapsed_time: int
    total_elevation_gain: float
    average_heartrate: float | None
    start_date: datetime

    # Visual for the card: the GPS trace and/or a photo, whichever the activity has.
    polyline: str | None
    photo_url: str | None
    # The lifts, for a gym session that was logged with them. Small enough to send whole:
    # a session is a handful of exercises, and the card decides how many to show.
    exercises: list[Exercise]


class GroupFeed(BaseModel):
    group_id: int
    group_name: str
    items: list[FeedItem]
    # Pass back as ?before= to load the next page; null when there is nothing older.
    next_before: datetime | None
