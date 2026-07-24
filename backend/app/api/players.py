"""Player stats: career + per-season + game log (BUILD_SPEC §6.4)."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_league_id, require_role
from app.core.errors import ApiError
from app.db.session import get_db
from app.models import Player, User
from app.schemas.player import PlayerDetailOut
from app.schemas.player_stats import GamelogEntry, PlayerStatsOut
from app.services.player_stats import build_career_stats, build_gamelog, build_per_season_stats

router = APIRouter(tags=["players"])

_require_admin = require_role("admin")


def _get_player_or_404(db: Session, player_id: int, league_id: int) -> Player:
    player = db.query(Player).filter(Player.id == player_id, Player.league_id == league_id).one_or_none()
    if player is None:
        raise ApiError(404, "player not found", "not_found")
    return player


@router.get("/players/{player_id}", response_model=PlayerDetailOut)
def get_player_detail(
    player_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(_require_admin),
    league_id: int = Depends(get_current_league_id),
) -> Player:
    """Admin-only, on-demand — the only endpoint that returns national_id
    (sensitive PII). List/roster responses (PlayerOut) never include it."""
    return _get_player_or_404(db, player_id, league_id)


@router.get("/players/{player_id}/stats", response_model=PlayerStatsOut)
def player_stats(
    player_id: int,
    season_id: int | None = Query(None),
    db: Session = Depends(get_db),
    league_id: int = Depends(get_current_league_id),
) -> dict:
    player = _get_player_or_404(db, player_id, league_id)
    return {
        "career": build_career_stats(db, player),
        "per_season": build_per_season_stats(db, player),
        "gamelog": build_gamelog(db, player, season_id),
    }


@router.get("/players/{player_id}/gamelog", response_model=list[GamelogEntry])
def player_gamelog(
    player_id: int,
    season_id: int | None = Query(None),
    db: Session = Depends(get_db),
    league_id: int = Depends(get_current_league_id),
) -> list[dict]:
    player = _get_player_or_404(db, player_id, league_id)
    return build_gamelog(db, player, season_id)
