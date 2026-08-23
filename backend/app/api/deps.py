"""Shared FastAPI dependencies.

Phase 3 adds get_current_athlete here; Phase 5 adds require_group_member.
"""

from collections.abc import Generator

from sqlmodel import Session

from app.infra.db import session_scope


def get_db() -> Generator[Session, None, None]:
    yield from session_scope()
