from datetime import datetime

from sqlalchemy import BigInteger, Column, ForeignKey
from sqlmodel import Field, SQLModel

from app.models.base import tz_column, utcnow


class Group(SQLModel, table=True):
    """A set of athletes who compare activity with each other.

    Unlike athletes and activities, group IDs are ours, so this one autoincrements.
    """

    __tablename__ = "groups"

    id: int | None = Field(default=None, primary_key=True)
    name: str
    invite_code: str = Field(unique=True, index=True)
    # Nullable + SET NULL: if the creator's account is deleted the group must
    # survive for its remaining members, so we drop the attribution, not the group.
    created_by: int | None = Field(
        default=None,
        sa_column=Column(
            BigInteger,
            ForeignKey("athletes.athlete_id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    created_at: datetime = Field(default_factory=utcnow, sa_column=tz_column(nullable=False))


class GroupMembership(SQLModel, table=True):
    """Join table: which athletes belong to which groups.

    Composite primary key means a repeated join is a no-op rather than a duplicate row.
    """

    __tablename__ = "group_memberships"

    group_id: int = Field(
        sa_column=Column(ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True)
    )
    athlete_id: int = Field(
        sa_column=Column(
            BigInteger,
            ForeignKey("athletes.athlete_id", ondelete="CASCADE"),
            primary_key=True,
            index=True,
        )
    )
    joined_at: datetime = Field(default_factory=utcnow, sa_column=tz_column(nullable=False))
