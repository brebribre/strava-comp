from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from app.config import get_settings

settings = get_settings()

engine = create_engine(settings.database_url, echo=False, pool_pre_ping=True)


# Columns and indexes added to tables that already existed in some environment.
#
# SQLModel.metadata.create_all() creates missing *tables* but never alters existing ones, so
# a column added to a shipped table appears on a fresh database and is silently absent in
# production. These statements are idempotent and cheap; they run on every boot.
#
# This is a stopgap for a real migration tool — every entry here is a reminder that Alembic
# is overdue.
_SCHEMA_PATCHES: tuple[str, ...] = (
    "ALTER TABLE IF EXISTS group_integrations ADD COLUMN IF NOT EXISTS telegram_chat_title VARCHAR",
    "ALTER TABLE IF EXISTS group_integrations ADD COLUMN IF NOT EXISTS pairing_code VARCHAR",
    "CREATE INDEX IF NOT EXISTS ix_group_integrations_pairing_code"
    " ON group_integrations (pairing_code)",
)


def create_db_and_tables() -> None:
    """Create tables for every model registered on SQLModel.metadata, then patch columns.

    Importing app.models is what registers them.
    """
    import app.models  # noqa: F401  (import for the side effect of registering tables)

    SQLModel.metadata.create_all(engine)

    with engine.begin() as connection:
        for statement in _SCHEMA_PATCHES:
            connection.exec_driver_sql(statement)


def session_scope() -> Generator[Session, None, None]:
    """Yield a session. Wrapped as a FastAPI dependency in app/api/deps.py."""
    with Session(engine) as session:
        yield session
