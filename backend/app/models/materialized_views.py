"""Unmapped Core `Table` defs for the leaderboard materialized views (§3.1).

DDL for these lives entirely in the Alembic migration (raw SQL) — they're
deliberately kept off `Base.metadata` so Alembic/`Base.metadata.create_all`
never try to manage them as ordinary tables. This module exists purely so
application code has a typed, queryable handle for SELECTs.
"""
from sqlalchemy import BigInteger, Column, MetaData, Table

_mv_metadata = MetaData()

mv_batting_season = Table(
    "mv_batting_season", _mv_metadata,
    Column("player_id", BigInteger),
    Column("league_id", BigInteger),
    Column("season_id", BigInteger),
    Column("team_id", BigInteger),
    Column("g", BigInteger),
    Column("pa", BigInteger),
    Column("ab", BigInteger),
    Column("r", BigInteger),
    Column("h", BigInteger),
    Column("b2", BigInteger),
    Column("b3", BigInteger),
    Column("hr", BigInteger),
    Column("rbi", BigInteger),
    Column("bb", BigInteger),
    Column("hp", BigInteger),
    Column("sf", BigInteger),
    Column("sh", BigInteger),
    Column("so", BigInteger),
    Column("sb", BigInteger),
    Column("cs", BigInteger),
)

mv_pitching_season = Table(
    "mv_pitching_season", _mv_metadata,
    Column("player_id", BigInteger),
    Column("league_id", BigInteger),
    Column("season_id", BigInteger),
    Column("team_id", BigInteger),
    Column("g", BigInteger),
    Column("gs", BigInteger),
    Column("w", BigInteger),
    Column("l", BigInteger),
    Column("sv", BigInteger),
    Column("cg", BigInteger),
    Column("sho", BigInteger),
    Column("outs", BigInteger),
    Column("np", BigInteger),
    Column("bf", BigInteger),
    Column("ab", BigInteger),
    Column("h", BigInteger),
    Column("hr", BigInteger),
    Column("bb", BigInteger),
    Column("hp", BigInteger),
    Column("so", BigInteger),
    Column("r", BigInteger),
    Column("er", BigInteger),
)
