import logging
from collections.abc import Generator
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect
from sqlmodel import Session, create_engine

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

engine = create_engine(settings.database_url, echo=False, pool_pre_ping=True)

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent


def _alembic_config() -> Config:
    """Alembic config with absolute paths, so it works whatever the working directory is."""
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "migrations"))
    return config


def run_migrations() -> None:
    """Bring the database up to the latest revision.

    Adopts a pre-Alembic database rather than failing on it: environments created by the old
    `SQLModel.metadata.create_all()` startup already have every table but no `alembic_version`,
    and running the baseline against them would fail on "table already exists". Stamping first
    records where they are, then the upgrade applies anything newer.
    """
    config = _alembic_config()
    inspector = inspect(engine)

    has_version_table = inspector.has_table("alembic_version")
    has_existing_schema = inspector.has_table("athletes")

    if has_existing_schema and not has_version_table:
        logger.info("adopting an existing pre-Alembic schema: stamping baseline")
        command.stamp(config, "head")

    command.upgrade(config, "head")
    logger.info("database migrations are up to date")


def session_scope() -> Generator[Session, None, None]:
    """Yield a session. Wrapped as a FastAPI dependency in app/api/deps.py."""
    with Session(engine) as session:
        yield session
