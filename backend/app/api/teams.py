"""Read-only, tenant-scoped team/player listing.

Full team CRUD, manual player add, and Excel roster import land in Phase 2 —
these GETs exist now to exercise and test the tenant-scoping dependency
(`get_current_league_id`) introduced in Phase 1.5.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_league_id
from app.core.errors import ApiError
from app.db.session import get_db
from app.models import Player, Team
from app.schemas.player import PlayerOut
from app.schemas.team import TeamOut

router = APIRouter(tags=["teams"])


@router.get("/teams", response_model=list[TeamOut])
def list_teams(
    db: Session = Depends(get_db),
    league_id: int = Depends(get_current_league_id),
) -> list[Team]:
    return db.query(Team).filter(Team.league_id == league_id).order_by(Team.id).all()


@router.get("/teams/{team_id}", response_model=TeamOut)
def get_team(
    team_id: int,
    db: Session = Depends(get_db),
    league_id: int = Depends(get_current_league_id),
) -> Team:
    team = db.query(Team).filter(Team.id == team_id, Team.league_id == league_id).one_or_none()
    if team is None:
        raise ApiError(404, "team not found", "not_found")
    return team


@router.get("/teams/{team_id}/players", response_model=list[PlayerOut])
def list_team_players(
    team_id: int,
    db: Session = Depends(get_db),
    league_id: int = Depends(get_current_league_id),
) -> list[Player]:
    team = db.query(Team).filter(Team.id == team_id, Team.league_id == league_id).one_or_none()
    if team is None:
        raise ApiError(404, "team not found", "not_found")
    return db.query(Player).filter(Player.team_id == team.id).order_by(Player.number).all()
