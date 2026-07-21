"""Read-only, tenant-scoped game listing.

Game creation, score entry, validation, and finalize land in Phase 3 — these
GETs exist now to exercise and test tenant scoping for the `games` table.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_league_id
from app.core.errors import ApiError
from app.db.session import get_db
from app.models import Game
from app.schemas.game import GameOut

router = APIRouter(tags=["games"])


@router.get("/games", response_model=list[GameOut])
def list_games(
    db: Session = Depends(get_db),
    league_id: int = Depends(get_current_league_id),
) -> list[Game]:
    return db.query(Game).filter(Game.league_id == league_id).order_by(Game.id).all()


@router.get("/games/{game_id}", response_model=GameOut)
def get_game(
    game_id: int,
    db: Session = Depends(get_db),
    league_id: int = Depends(get_current_league_id),
) -> Game:
    game = db.query(Game).filter(Game.id == game_id, Game.league_id == league_id).one_or_none()
    if game is None:
        raise ApiError(404, "game not found", "not_found")
    return game
