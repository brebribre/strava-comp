from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from app.models.base import tz_column, utcnow


class Activity(SQLModel, table=True):
    """One Strava activity, owned by one athlete.

    The primary key is Strava's activity ID (BIGINT — these already exceed int32),
    which makes the webhook/backfill writes in Phases 6-7 a plain upsert with no
    dedupe logic.
    """

    __tablename__ = "activities"
    __table_args__ = (
        # Phase 8 filters by owner within a date window; Phase 6 backfills per athlete.
        # Its leftmost column also serves plain owner_id lookups, so no separate index.
        Index("ix_activities_owner_start", "owner_id", "start_date"),
    )

    id: int = Field(sa_column=Column(BigInteger, primary_key=True, autoincrement=False))
    owner_id: int = Field(
        sa_column=Column(
            BigInteger,
            ForeignKey("athletes.athlete_id", ondelete="CASCADE"),
            nullable=False,
        )
    )

    name: str | None = None
    sport_type: str | None = Field(default=None, index=True)

    distance: float | None = None              # metres
    moving_time: int | None = None             # seconds
    elapsed_time: int | None = None            # seconds
    total_elevation_gain: float | None = None  # metres
    average_heartrate: float | None = None
    max_heartrate: float | None = None

    start_date: datetime | None = Field(default=None, sa_column=tz_column(nullable=True, index=True))
    # The wall clock the athlete actually trained by, stored without a zone: Strava gives us
    # start_date_local, and a target's "day" and "week" mean the athlete's, not UTC's. A
    # brother in Sydney finishing at 08:00 Monday must not land in Sunday's week.
    start_date_local: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=False), nullable=True)
    )
    # Seconds east of UTC at the time of the activity, straight from Strava.
    utc_offset: int | None = None

    # Full Strava payload, so new fields can be backfilled without re-fetching.
    raw_data: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB, nullable=True))

    created_at: datetime = Field(default_factory=utcnow, sa_column=tz_column(nullable=False))
    updated_at: datetime = Field(default_factory=utcnow, sa_column=tz_column(nullable=False))
