from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (register models on Base.metadata)
from app.core.config import get_settings
from app.core.security import create_access_token, hash_password
from app.db.session import get_db as get_db_dependency
from app.main import app as fastapi_app
from app.models import League, User

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


@pytest.fixture
def client(db_session):
    """TestClient wired to the test's own rolled-back db_session, so writes
    made through ORM helpers in a test are visible to the API and vice versa.
    """

    def _override_get_db():
        yield db_session

    fastapi_app.dependency_overrides[get_db_dependency] = _override_get_db
    try:
        yield TestClient(fastapi_app)
    finally:
        fastapi_app.dependency_overrides.pop(get_db_dependency, None)


def make_league(db_session, name: str = "Test League", slug: str = "test-league") -> League:
    league = League(name=name, slug=slug)
    db_session.add(league)
    db_session.flush()
    return league


def make_user(
    db_session,
    *,
    email: str,
    role: str,
    league_id: int | None,
    password: str = "TestPass123!",
    display_name: str = "Test User",
) -> User:
    user = User(
        email=email,
        role=role,
        league_id=league_id,
        password_hash=hash_password(password),
        display_name=display_name,
    )
    db_session.add(user)
    db_session.flush()
    return user


def auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(user_id=user.id, role=user.role, league_id=user.league_id)
    return {"Authorization": f"Bearer {token}"}
