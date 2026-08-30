from datetime import datetime

from sqlalchemy import BigInteger, Column, ForeignKey, Index, Text
from sqlmodel import Field, SQLModel

from app.models.base import tz_column, utcnow


class PushSubscription(SQLModel, table=True):
    """One browser, on one device, that has agreed to receive notifications.

    Keyed by the endpoint URL the push service hands out, which is what makes a
    subscription unique — the same athlete has a separate row per phone and per browser,
    and re-subscribing on the same device returns the same endpoint rather than a second
    row.
    """

    __tablename__ = "push_subscriptions"
    __table_args__ = (Index("ix_push_subscriptions_athlete", "athlete_id"),)

    # The endpoint is the identity. It is long (Apple's run to a few hundred characters),
    # so TEXT rather than a bounded varchar.
    endpoint: str = Field(sa_column=Column(Text, primary_key=True))

    athlete_id: int = Field(
        sa_column=Column(
            BigInteger,
            ForeignKey("athletes.athlete_id", ondelete="CASCADE"),
            nullable=False,
        )
    )

    # The browser's public key and auth secret, used to encrypt each payload so the push
    # service relays something it cannot read.
    p256dh: str = Field(sa_column=Column(Text, nullable=False))
    auth: str = Field(sa_column=Column(Text, nullable=False))

    # Whatever the browser called itself when subscribing, so the UI can say which device
    # this is when someone has several.
    user_agent: str | None = Field(default=None, sa_column=Column(Text, nullable=True))

    created_at: datetime = Field(default_factory=utcnow, sa_column=tz_column(nullable=False))
    # Bumped on every successful send, so a stale device is recognisable.
    last_used_at: datetime | None = Field(default=None, sa_column=tz_column(nullable=True))
