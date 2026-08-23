"""Shared FastAPI dependencies.

Phase 5 adds require_group_member here.
"""

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlmodel import Session

from app.config import get_settings
from app.infra.db import session_scope
from app.models import Athlete
from app.services.session import read_session_token


def get_db() -> Generator[Session, None, None]:
    yield from session_scope()


DbSession = Annotated[Session, Depends(get_db)]


def get_current_athlete(request: Request, session: DbSession) -> Athlete:
    """Resolve the logged-in athlete from the signed session cookie, or 401."""
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
    )

    token = request.cookies.get(get_settings().session_cookie_name)
    if not token:
        raise unauthorized

    athlete_id = read_session_token(token)
    if athlete_id is None:
        raise unauthorized

    athlete = session.get(Athlete, athlete_id)
    if athlete is None:
        # Validly signed cookie for an athlete that no longer exists.
        raise unauthorized
    return athlete


CurrentAthlete = Annotated[Athlete, Depends(get_current_athlete)]
