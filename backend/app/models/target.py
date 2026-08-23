from datetime import datetime
from typing import Any

from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from app.models.base import tz_column, utcnow


class GroupTarget(SQLModel, table=True):
    """A group's shared training target.

    One target per group — group_id is the primary key, so setting a target twice
    updates it rather than accumulating rows.
    """

    __tablename__ = "group_targets"

    group_id: int = Field(
        sa_column=Column(ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True)
    )

    # "count exercises per period", e.g. 4 per week.
    count: int
    period: str  # week | month | year

    # The target stops applying after this date.
    until: datetime = Field(sa_column=tz_column(nullable=False))

    # What counts as an exercise, per sport. JSONB so adding a sport or a new kind of
    # threshold doesn't need a migration.
    rules: dict[str, Any] = Field(sa_column=Column(JSONB, nullable=False))

    created_at: datetime = Field(default_factory=utcnow, sa_column=tz_column(nullable=False))
    updated_at: datetime = Field(default_factory=utcnow, sa_column=tz_column(nullable=False))
