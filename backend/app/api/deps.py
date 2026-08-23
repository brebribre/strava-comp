"""Shared FastAPI dependencies."""

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlmodel import Session

from app.config import get_settings
from app.infra.db import session_scope
from app.models import Athlete, Group
from app.services import groups as groups_service
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


def require_group_member(group_id: int, athlete: CurrentAthlete, session: DbSession) -> Group:
    """Guard every group-scoped endpoint: 404 if the group is gone, 403 if not a member.

    Returns the Group so routes don't have to load it again.
    """
    group = session.get(Group, group_id)
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    if not groups_service.is_member(session, group_id, athlete.athlete_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this group"
        )
    return group


MemberGroup = Annotated[Group, Depends(require_group_member)]
