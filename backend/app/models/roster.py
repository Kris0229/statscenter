from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import (
    entity_status_enum,
    player_status_enum,
    roster_req_status_enum,
    roster_req_type_enum,
)


class Season(Base):
    __tablename__ = "seasons"
    __table_args__ = (Index("idx_seasons_league", "league_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    league_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("leagues.id"), nullable=False,
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    innings_per_game: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="7",
    )
    pa_qualifier_factor: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), nullable=False, server_default="2.00",
    )
    ip_qualifier_factor: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), nullable=False, server_default="1.00",
    )
    is_current: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )


class Team(Base):
    __tablename__ = "teams"
    __table_args__ = (
        UniqueConstraint("league_id", "name", name="uq_teams_league_name"),
        Index("idx_teams_league", "league_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    league_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("leagues.id"), nullable=False,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    logo_url: Mapped[str | None] = mapped_column(Text)
    captain_user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id"),
    )
    status: Mapped[str] = mapped_column(
        entity_status_enum, nullable=False, server_default="active",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )


class Player(Base):
    __tablename__ = "players"
    __table_args__ = (
        CheckConstraint("number BETWEEN 0 AND 99", name="ck_players_number_range"),
        CheckConstraint("bats IN ('R','L','S')", name="ck_players_bats"),
        CheckConstraint("throws IN ('R','L')", name="ck_players_throws"),
        UniqueConstraint(
            "team_id", "number",
            name="uq_players_team_number",
            deferrable=True, initially="DEFERRED",
        ),
        Index("idx_players_league", "league_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    league_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("leagues.id"), nullable=False,
    )
    team_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("teams.id"), nullable=False,
    )
    user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id"),
    )
    # RESERVED for future cross-league identity; keep NULL for now (§1.3).
    person_id: Mapped[int | None] = mapped_column(BigInteger)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    positions: Mapped[str | None] = mapped_column(Text)
    bats: Mapped[str | None] = mapped_column(Text)      # CHAR(1) in DDL, but stored as text w/ CHECK
    throws: Mapped[str | None] = mapped_column(Text)
    photo_url: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        player_status_enum, nullable=False, server_default="active",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )


class RosterChangeRequest(Base):
    __tablename__ = "roster_change_requests"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    league_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("leagues.id"), nullable=False,
    )
    team_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("teams.id"), nullable=False,
    )
    type: Mapped[str] = mapped_column(roster_req_type_enum, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(
        roster_req_status_enum, nullable=False, server_default="pending",
    )
    reason: Mapped[str | None] = mapped_column(Text)
    requested_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False,
    )
    reviewed_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
