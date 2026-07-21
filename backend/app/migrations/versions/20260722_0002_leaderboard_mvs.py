"""leaderboard materialized views (§3.1)

Revision ID: 20260722_0002
Revises: 20260721_0001
Create Date: 2026-07-22
"""
from typing import Sequence, Union

from alembic import op

revision: str = "20260722_0002"
down_revision: Union[str, None] = "20260721_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_MV_BATTING_SEASON = """
CREATE MATERIALIZED VIEW mv_batting_season AS
SELECT p.id AS player_id, g.league_id, g.season_id, p.team_id,
       COUNT(DISTINCT bl.game_id) AS g,
       SUM(bl.pa) pa, SUM(bl.ab) ab, SUM(bl.r) r, SUM(bl.h) h,
       SUM(bl.b2) b2, SUM(bl.b3) b3, SUM(bl.hr) hr, SUM(bl.rbi) rbi,
       SUM(bl.bb) bb, SUM(bl.hp) hp, SUM(bl.sf) sf, SUM(bl.sh) sh,
       SUM(bl.so) so, SUM(bl.sb) sb, SUM(bl.cs) cs
FROM batting_lines bl
JOIN games g   ON g.id = bl.game_id AND g.status = 'final'
JOIN players p ON p.id = bl.player_id
GROUP BY p.id, g.league_id, g.season_id, p.team_id
"""

_MV_PITCHING_SEASON = """
CREATE MATERIALIZED VIEW mv_pitching_season AS
SELECT p.id AS player_id, g.league_id, g.season_id, p.team_id,
       COUNT(DISTINCT pl.game_id) AS g,
       SUM(CASE WHEN pl.gs THEN 1 ELSE 0 END) gs,
       SUM(CASE WHEN pl.decision='W' THEN 1 ELSE 0 END) w,
       SUM(CASE WHEN pl.decision='L' THEN 1 ELSE 0 END) l,
       SUM(CASE WHEN pl.decision='SV' THEN 1 ELSE 0 END) sv,
       SUM(CASE WHEN pl.cg THEN 1 ELSE 0 END) cg,
       SUM(CASE WHEN pl.sho THEN 1 ELSE 0 END) sho,
       SUM(pl.outs) outs, SUM(pl.np) np, SUM(pl.bf) bf, SUM(pl.ab) ab,
       SUM(pl.h) h, SUM(pl.hr) hr, SUM(pl.bb) bb, SUM(pl.hp) hp,
       SUM(pl.so) so, SUM(pl.r) r, SUM(pl.er) er
FROM pitching_lines pl
JOIN games g   ON g.id = pl.game_id AND g.status = 'final'
JOIN players p ON p.id = pl.player_id
GROUP BY p.id, g.league_id, g.season_id, p.team_id
"""


def upgrade() -> None:
    op.execute(_MV_BATTING_SEASON)
    op.execute(
        "CREATE UNIQUE INDEX ux_mv_batting_season_player_season "
        "ON mv_batting_season(player_id, season_id)",
    )
    op.execute(
        "CREATE INDEX idx_mv_batting_season_league ON mv_batting_season(league_id, season_id)",
    )

    op.execute(_MV_PITCHING_SEASON)
    op.execute(
        "CREATE UNIQUE INDEX ux_mv_pitching_season_player_season "
        "ON mv_pitching_season(player_id, season_id)",
    )
    op.execute(
        "CREATE INDEX idx_mv_pitching_season_league ON mv_pitching_season(league_id, season_id)",
    )


def downgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_pitching_season")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_batting_season")
