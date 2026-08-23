from sqlalchemy import text
from sqlmodel import Session


def check_database(session: Session) -> bool:
    """Return True if a trivial query against Postgres succeeds."""
    session.exec(text("SELECT 1"))
    return True
