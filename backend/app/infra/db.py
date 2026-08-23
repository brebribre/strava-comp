from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from app.config import get_settings

settings = get_settings()

engine = create_engine(settings.database_url, echo=False, pool_pre_ping=True)


def create_db_and_tables() -> None:
    """Create tables for every model registered on SQLModel.metadata.

    Importing app.models is what registers them. Replaced by Alembic later.
    """
    import app.models  # noqa: F401  (import for the side effect of registering tables)

    SQLModel.metadata.create_all(engine)


def session_scope() -> Generator[Session, None, None]:
    """Yield a session. Wrapped as a FastAPI dependency in app/api/deps.py."""
    with Session(engine) as session:
        yield session
