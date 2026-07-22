"""Read-only, tenant-scoped season listing.

Not part of any BUILD_SPEC §6 contract block — added because the frontend
(Phase 6) needs a way to discover season_id when creating a game, and
nothing else in the API exposes it.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_league_id
from app.db.session import get_db
from app.models import Season
from app.schemas.season import SeasonOut

router = APIRouter(tags=["seasons"])


@router.get("/seasons", response_model=list[SeasonOut])
def list_seasons(
    db: Session = Depends(get_db),
    league_id: int = Depends(get_current_league_id),
) -> list[Season]:
    return (
        db.query(Season)
        .filter(Season.league_id == league_id)
        .order_by(Season.year.desc())
        .all()
    )
