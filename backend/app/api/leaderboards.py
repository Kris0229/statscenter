"""Minimal, tenant-scoped batting leaderboard.

TODO(confirm): Phase 4 replaces this with the `mv_batting_season` materialized
view (§3.1), full rate-stat formulas (§4), and qualifier/sort/pagination
support. This bare aggregation exists in Phase 1.5 only to prove and test
that leaderboard reads are tenant-scoped like every other league-scoped query.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_league_id
from app.db.session import get_db
from app.models import BattingLine, Game, Player
from app.schemas.leaderboard import BattingLeaderboardRow

router = APIRouter(tags=["leaderboards"])


@router.get("/leaderboards/batting", response_model=list[BattingLeaderboardRow])
def batting_leaderboard(
    db: Session = Depends(get_db),
    league_id: int = Depends(get_current_league_id),
) -> list[BattingLeaderboardRow]:
    rows = (
        db.query(
            Player.id.label("player_id"),
            Player.team_id.label("team_id"),
            Player.name.label("name"),
            func.count(func.distinct(BattingLine.game_id)).label("g"),
            func.coalesce(func.sum(BattingLine.pa), 0).label("pa"),
            func.coalesce(func.sum(BattingLine.ab), 0).label("ab"),
            func.coalesce(func.sum(BattingLine.h), 0).label("h"),
            func.coalesce(func.sum(BattingLine.hr), 0).label("hr"),
            func.coalesce(func.sum(BattingLine.rbi), 0).label("rbi"),
            func.coalesce(func.sum(BattingLine.bb), 0).label("bb"),
            func.coalesce(func.sum(BattingLine.so), 0).label("so"),
        )
        .join(BattingLine, BattingLine.player_id == Player.id)
        .join(Game, Game.id == BattingLine.game_id)
        .filter(
            Player.league_id == league_id,
            Game.league_id == league_id,
            Game.status == "final",
        )
        .group_by(Player.id, Player.team_id, Player.name)
        .order_by(Player.id)
        .all()
    )
    return [BattingLeaderboardRow(**row._mapping) for row in rows]
