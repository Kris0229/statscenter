"""initial schema — all §3 tables

Revision ID: 20260721_0001
Revises:
Create Date: 2026-07-21
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260721_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---- ENUM definitions (create_type=False; created explicitly below) ----
_ENUMS = {
    "entity_status": ("active", "inactive"),
    "user_role": ("super_admin", "admin", "power", "user"),
    "player_status": ("active", "left"),
    "roster_req_type": ("rename", "renumber", "add", "remove"),
    "roster_req_status": ("pending", "approved", "rejected"),
    "game_status": ("scheduled", "in_progress", "final", "postponed", "cancelled"),
    "pitch_decision": ("W", "L", "SV", "BS", "HLD", "SVO", "none"),
    "media_type": ("photo", "video", "link"),
}


def _e(name: str) -> postgresql.ENUM:
    return postgresql.ENUM(*_ENUMS[name], name=name, create_type=False)


def upgrade() -> None:
    conn = op.get_bind()

    op.execute("CREATE EXTENSION IF NOT EXISTS citext")

    for name, values in _ENUMS.items():
        postgresql.ENUM(*values, name=name, create_type=True).create(conn, checkfirst=True)

    op.create_table(
        "leagues",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False, unique=True),
        sa.Column("logo_url", sa.Text()),
        sa.Column("status", _e("entity_status"), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("league_id", sa.BigInteger(), sa.ForeignKey("leagues.id")),
        sa.Column("email", postgresql.CITEXT(), nullable=False, unique=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("role", _e("user_role"), nullable=False, server_default="user"),
        sa.Column("status", _e("entity_status"), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.CheckConstraint(
            "(role = 'super_admin' AND league_id IS NULL)"
            " OR (role <> 'super_admin' AND league_id IS NOT NULL)",
            name="ck_users_tenancy",
        ),
    )
    op.create_index("idx_users_league", "users", ["league_id"])

    op.create_table(
        "seasons",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("league_id", sa.BigInteger(), sa.ForeignKey("leagues.id"), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("innings_per_game", sa.Integer(), nullable=False, server_default="7"),
        sa.Column("pa_qualifier_factor", sa.Numeric(4, 2), nullable=False, server_default="2.00"),
        sa.Column("ip_qualifier_factor", sa.Numeric(4, 2), nullable=False, server_default="1.00"),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("idx_seasons_league", "seasons", ["league_id"])

    op.create_table(
        "teams",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("league_id", sa.BigInteger(), sa.ForeignKey("leagues.id"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("logo_url", sa.Text()),
        sa.Column("captain_user_id", sa.BigInteger(), sa.ForeignKey("users.id")),
        sa.Column("status", _e("entity_status"), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint("league_id", "name", name="uq_teams_league_name"),
    )
    op.create_index("idx_teams_league", "teams", ["league_id"])

    op.create_table(
        "players",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("league_id", sa.BigInteger(), sa.ForeignKey("leagues.id"), nullable=False),
        sa.Column("team_id", sa.BigInteger(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id")),
        sa.Column("person_id", sa.BigInteger()),  # RESERVED for future cross-league identity
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("number", sa.SmallInteger(), nullable=False),
        sa.Column("positions", sa.Text()),
        sa.Column("bats", sa.Text()),
        sa.Column("throws", sa.Text()),
        sa.Column("photo_url", sa.Text()),
        sa.Column("status", _e("player_status"), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.CheckConstraint("number BETWEEN 0 AND 99", name="ck_players_number_range"),
        sa.CheckConstraint("bats IN ('R','L','S')", name="ck_players_bats"),
        sa.CheckConstraint("throws IN ('R','L')", name="ck_players_throws"),
        sa.UniqueConstraint(
            "team_id", "number",
            name="uq_players_team_number",
            deferrable=True, initially="DEFERRED",
        ),
    )
    op.create_index("idx_players_league", "players", ["league_id"])

    op.create_table(
        "roster_change_requests",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("league_id", sa.BigInteger(), sa.ForeignKey("leagues.id"), nullable=False),
        sa.Column("team_id", sa.BigInteger(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("type", _e("roster_req_type"), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("status", _e("roster_req_status"), nullable=False, server_default="pending"),
        sa.Column("reason", sa.Text()),
        sa.Column("requested_by", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reviewed_by", sa.BigInteger(), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "games",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("league_id", sa.BigInteger(), sa.ForeignKey("leagues.id"), nullable=False),
        sa.Column("season_id", sa.BigInteger(), sa.ForeignKey("seasons.id"), nullable=False),
        sa.Column("game_date", sa.Date(), nullable=False),
        sa.Column("start_time", sa.Time()),
        sa.Column("venue", sa.Text()),
        sa.Column("game_type", sa.Text(), nullable=False, server_default="regular"),
        sa.Column("home_team_id", sa.BigInteger(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("away_team_id", sa.BigInteger(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("status", _e("game_status"), nullable=False, server_default="scheduled"),
        sa.Column("line_score", postgresql.JSONB()),
        sa.Column("code", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("finalized_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("home_team_id <> away_team_id", name="ck_games_teams_differ"),
    )
    op.create_index("idx_games_season", "games", ["season_id", "status"])
    op.create_index("idx_games_league", "games", ["league_id", "status"])

    op.create_table(
        "batting_lines",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("game_id", sa.BigInteger(),
                  sa.ForeignKey("games.id", ondelete="CASCADE"), nullable=False),
        sa.Column("player_id", sa.BigInteger(), sa.ForeignKey("players.id"), nullable=False),
        sa.Column("bat_order", sa.SmallInteger()),
        sa.Column("sub_index", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("pos", sa.Text()),
        # PA breakdown
        sa.Column("pa", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("ab", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("sh", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("sf", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("bb", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("hp", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("io", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("tie", sa.SmallInteger(), nullable=False, server_default="0"),
        # Results
        sa.Column("r", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("h", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("b2", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("b3", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("hr", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("rbi", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("so", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("sb", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("cs", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("gidp", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("e", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.UniqueConstraint("game_id", "player_id", name="uq_batting_lines_game_player"),
        sa.CheckConstraint("h >= b2 + b3 + hr", name="ck_batting_h_min"),
        sa.CheckConstraint(
            "pa = ab + sh + sf + bb + hp + io + tie", name="ck_batting_pa_breakdown",
        ),
    )
    op.create_index("idx_batting_game", "batting_lines", ["game_id"])
    op.create_index("idx_batting_player", "batting_lines", ["player_id"])

    op.create_table(
        "pitching_lines",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("game_id", sa.BigInteger(),
                  sa.ForeignKey("games.id", ondelete="CASCADE"), nullable=False),
        sa.Column("player_id", sa.BigInteger(), sa.ForeignKey("players.id"), nullable=False),
        sa.Column("seq", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column("decision", _e("pitch_decision"), nullable=False, server_default="none"),
        sa.Column("outs", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("np", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("bf", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("ab", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("h", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("hr", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("bb", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("hp", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("so", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("r", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("er", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("wp", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("gs", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("cg", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("sho", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("sv", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("svo", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.UniqueConstraint(
            "game_id", "player_id", "seq", name="uq_pitching_lines_game_player_seq",
        ),
        sa.CheckConstraint("er <= r", name="ck_pitching_er_le_r"),
    )
    op.create_index("idx_pitching_game", "pitching_lines", ["game_id"])
    op.create_index("idx_pitching_player", "pitching_lines", ["player_id"])

    op.create_table(
        "media",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("game_id", sa.BigInteger(), sa.ForeignKey("games.id")),
        sa.Column("player_id", sa.BigInteger(), sa.ForeignKey("players.id")),
        sa.Column("uploader_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("type", _e("media_type"), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("status", _e("entity_status"), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    op.create_table(
        "reports",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("game_id", sa.BigInteger(), sa.ForeignKey("games.id"), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("content", sa.Text()),
        sa.Column("cover_media_id", sa.BigInteger(), sa.ForeignKey("media.id")),
        sa.Column("author_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("entity", sa.Text(), nullable=False),
        sa.Column("entity_id", sa.BigInteger(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("before", postgresql.JSONB()),
        sa.Column("after", postgresql.JSONB()),
        sa.Column("actor_id", sa.BigInteger(), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )


def downgrade() -> None:
    conn = op.get_bind()

    # Drop tables in reverse dependency order.
    for table in [
        "audit_logs",
        "reports",
        "media",
        "pitching_lines",
        "batting_lines",
        "games",
        "roster_change_requests",
        "players",
        "teams",
        "seasons",
        "users",
        "leagues",
    ]:
        op.drop_table(table)

    for name in reversed(list(_ENUMS.keys())):
        postgresql.ENUM(name=name).drop(conn, checkfirst=True)
