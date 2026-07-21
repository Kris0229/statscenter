"""Leaderboards (BUILD_SPEC §6.4), backed by the season materialized views."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_league_id
from app.db.session import get_db
from app.schemas.leaderboard import BattingLeaderboardRow, PitchingLeaderboardRow
from app.services.leaderboard import (
    build_batting_leaderboard,
    build_pitching_leaderboard,
    resolve_season,
)

router = APIRouter(tags=["leaderboards"])


@router.get("/leaderboards/batting", response_model=list[BattingLeaderboardRow])
def batting_leaderboard(
    season_id: int | None = Query(None),
    team_id: int | None = Query(None),
    sort: str = Query("hr"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    qualified: bool = Query(True),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    league_id: int = Depends(get_current_league_id),
) -> list[dict]:
    season = resolve_season(db, league_id, season_id)
    return build_batting_leaderboard(
        db, league_id, season, team_id, sort, order, qualified, limit, offset,
    )


@router.get("/leaderboards/pitching", response_model=list[PitchingLeaderboardRow])
def pitching_leaderboard(
    season_id: int | None = Query(None),
    team_id: int | None = Query(None),
    sort: str = Query("era"),
    order: str = Query("asc", pattern="^(asc|desc)$"),
    qualified: bool = Query(True),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    league_id: int = Depends(get_current_league_id),
) -> list[dict]:
    season = resolve_season(db, league_id, season_id)
    return build_pitching_leaderboard(
        db, league_id, season, team_id, sort, order, qualified, limit, offset,
    )
