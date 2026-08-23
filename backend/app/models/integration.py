from datetime import datetime

from sqlalchemy import BigInteger, Column, ForeignKey
from sqlmodel import Field, SQLModel

from app.models.base import tz_column, utcnow


class GroupIntegration(SQLModel, table=True):
    """Where a group's notifications go.

    A separate table rather than columns on `groups`: SQLModel's create_all makes new
    tables but never alters existing ones, so a new column would appear on a fresh local
    database and be silently missing in production. It also leaves room for Discord later.
    """

    __tablename__ = "group_integrations"

    group_id: int = Field(
        sa_column=Column(ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True)
    )

    # Telegram chat IDs are negative for groups and can exceed int32.
    telegram_chat_id: int | None = Field(default=None, sa_column=Column(BigInteger, nullable=True))
    # Human-readable name of the connected chat, so the UI can confirm *which* group.
    telegram_chat_title: str | None = None

    # Short code the user sends as "/connect <code>" in their Telegram chat. This is how
    # the bot learns the chat id without anyone having to look one up.
    pairing_code: str | None = Field(default=None, index=True)

    created_at: datetime = Field(default_factory=utcnow, sa_column=tz_column(nullable=False))
    updated_at: datetime = Field(default_factory=utcnow, sa_column=tz_column(nullable=False))


class ActivityNotification(SQLModel, table=True):
    """One row per (activity, group) already announced.

    Strava fires `create` and often a follow-up `update` for the same activity, so without
    this the group gets the same post twice.
    """

    __tablename__ = "activity_notifications"

    activity_id: int = Field(
        sa_column=Column(
            BigInteger, ForeignKey("activities.id", ondelete="CASCADE"), primary_key=True
        )
    )
    group_id: int = Field(
        sa_column=Column(ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True)
    )
    sent_at: datetime = Field(default_factory=utcnow, sa_column=tz_column(nullable=False))
