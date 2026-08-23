"""Shared helpers for table definitions."""

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime


def utcnow() -> datetime:
    return datetime.now(UTC)


def tz_column(**kwargs) -> Column:
    """A TIMESTAMPTZ column.

    SQLModel maps a plain `datetime` to TIMESTAMP WITHOUT TIME ZONE, which would
    silently drop the offset on Strava's UTC timestamps. Every datetime in the
    schema goes through here instead.
    """
    return Column(DateTime(timezone=True), **kwargs)
