from datetime import date, datetime, time

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import game_status_enum, pitch_decision_enum


class Game(Base):
    __tablename__ = "games"
    __table_args__ = (
        CheckConstraint("home_team_id <> away_team_id", name="ck_games_teams_differ"),
        Index("idx_games_season", "season_id", "status"),
        Index("idx_games_league", "league_id", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    league_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("leagues.id"), nullable=False,
    )
    season_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("seasons.id"), nullable=False,
    )
    game_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time | None] = mapped_column(Time)
    venue: Mapped[str | None] = mapped_column(Text)
    game_type: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="regular",
    )
    home_team_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("teams.id"), nullable=False,
    )
    away_team_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("teams.id"), nullable=False,
    )
    status: Mapped[str] = mapped_column(
        game_status_enum, nullable=False, server_default="scheduled",
    )
    line_score: Mapped[dict | None] = mapped_column(JSONB)
    code: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BattingLine(Base):
    __tablename__ = "batting_lines"
    __table_args__ = (
        UniqueConstraint("game_id", "player_id", name="uq_batting_lines_game_player"),
        CheckConstraint("h >= b2 + b3 + hr", name="ck_batting_h_min"),
        CheckConstraint(
            "pa = ab + sh + sf + bb + hp + io + tie", name="ck_batting_pa_breakdown",
        ),
        Index("idx_batting_game", "game_id"),
        Index("idx_batting_player", "player_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    game_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("games.id", ondelete="CASCADE"), nullable=False,
    )
    player_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("players.id"), nullable=False,
    )
    bat_order: Mapped[int | None] = mapped_column(SmallInteger)
    sub_index: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    pos: Mapped[str | None] = mapped_column(Text)

    # PA breakdown
    pa: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    ab: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    sh: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    sf: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    bb: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    hp: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    io: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    tie: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")

    # Results
    r: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    h: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    b2: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    b3: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    hr: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    rbi: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    so: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    sb: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    cs: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    gidp: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    e: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")


class PitchingLine(Base):
    __tablename__ = "pitching_lines"
    __table_args__ = (
        UniqueConstraint(
            "game_id", "player_id", "seq", name="uq_pitching_lines_game_player_seq",
        ),
        CheckConstraint("er <= r", name="ck_pitching_er_le_r"),
        Index("idx_pitching_game", "game_id"),
        Index("idx_pitching_player", "player_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    game_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("games.id", ondelete="CASCADE"), nullable=False,
    )
    player_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("players.id"), nullable=False,
    )
    seq: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="1")
    decision: Mapped[str] = mapped_column(
        pitch_decision_enum, nullable=False, server_default="none",
    )
    outs: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    np: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    bf: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    ab: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    h: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    hr: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    bb: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    hp: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    so: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    r: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    er: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    wp: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    gs: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    cg: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    sho: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    sv: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    svo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
