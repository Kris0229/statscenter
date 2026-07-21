from alembic import command
from sqlalchemy import inspect, text

from tests.conftest import alembic_config

EXPECTED_TABLES = {
    "leagues", "users", "seasons", "teams", "players",
    "roster_change_requests", "games", "batting_lines", "pitching_lines",
    "media", "reports", "audit_logs",
}


def test_upgrade_head_on_empty_db(db_engine) -> None:
    with db_engine.begin() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))

    command.upgrade(alembic_config(), "head")

    with db_engine.connect() as conn:
        tables = set(inspect(conn).get_table_names())
    assert EXPECTED_TABLES.issubset(tables)


def test_downgrade_base_then_upgrade_head_is_clean(db_engine) -> None:
    with db_engine.begin() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))

    cfg = alembic_config()
    command.upgrade(cfg, "head")

    command.downgrade(cfg, "base")
    with db_engine.connect() as conn:
        tables = set(inspect(conn).get_table_names())
    assert not (EXPECTED_TABLES & tables)

    command.upgrade(cfg, "head")
    with db_engine.connect() as conn:
        tables = set(inspect(conn).get_table_names())
    assert EXPECTED_TABLES.issubset(tables)
