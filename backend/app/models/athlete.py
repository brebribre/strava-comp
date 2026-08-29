from datetime import datetime

from sqlalchemy import BigInteger, Column
from sqlmodel import Field, SQLModel

from app.models.base import tz_column, utcnow


class Athlete(SQLModel, table=True):
    """A Strava user who has authorized the app.

    The primary key is Strava's own athlete ID — reusing it means webhook payloads
    and activity owner IDs join straight onto this table with no lookup. It is
    supplied by Strava, never generated here, hence autoincrement=False.
    """

    __tablename__ = "athletes"

    athlete_id: int = Field(
        sa_column=Column(BigInteger, primary_key=True, autoincrement=False)
    )
    name: str
    access_token: str
    refresh_token: str
    token_expires_at: datetime = Field(sa_column=tz_column(nullable=False))
    # Seconds east of UTC, taken from their most recent activity. Deciding which week is
    # "this week" needs their current local date, and Strava's athlete record doesn't carry
    # a timezone — their latest activity is the best evidence of where they are.
    utc_offset: int | None = None
    created_at: datetime = Field(default_factory=utcnow, sa_column=tz_column(nullable=False))
