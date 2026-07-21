from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (register models on Base.metadata)
from app.core.config import get_settings

BACKEND_DIR = Path(__file__).resolve().parent.parent


def alembic_config() -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "app" / "migrations"))
    return cfg


@pytest.fixture(scope="session")
def db_engine():
    db_url = get_settings().DATABASE_URL
    engine = create_engine(db_url, future=True)
    try:
        with engine.connect():
            pass
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"Postgres not reachable at {db_url}: {exc}")
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def migrated_schema(db_engine):
    """Reset to a clean schema and run migrations to head, once per session.

    Only tests that need a real schema (via `db_session`) pull this in, so
    schema-less tests (e.g. the health check) don't require Postgres at all.
    """
    with db_engine.begin() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    command.upgrade(alembic_config(), "head")
    yield


@pytest.fixture
def db_session(db_engine, migrated_schema):
    """A DB session whose writes are rolled back after each test.

    Uses SAVEPOINTs for the session's own commits/rollbacks so a mid-test
    `session.rollback()` (e.g. after an expected IntegrityError) doesn't
    tear down the outer transaction the fixture relies on for cleanup.
    """
    connection = db_engine.connect()
    trans = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint", future=True)
    try:
        yield session
    finally:
        session.close()
        trans.rollback()
        connection.close()
