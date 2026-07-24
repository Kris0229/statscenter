"""Tenant-scoped season listing + creation.

GET was added because the frontend (Phase 6) needs a way to discover
season_id when creating a game; POST closes a gap found during account/
schedule-management work — a freshly created league had no way to get its
first season without going through the seed script.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_league_id, require_role
from app.core.errors import ApiError
from app.db.session import get_db
from app.models import Season, User
from app.schemas.season import SeasonCreate, SeasonOut

router = APIRouter(tags=["seasons"])

_require_admin = require_role("admin")


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


@router.post("/seasons", response_model=SeasonOut, status_code=201)
def create_season(
    payload: SeasonCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(_require_admin),
    league_id: int = Depends(get_current_league_id),
) -> Season:
    if payload.is_current:
        db.query(Season).filter(Season.league_id == league_id).update(
            {"is_current": False}, synchronize_session=False,
        )

    season = Season(
        league_id=league_id, year=payload.year, name=payload.name,
        innings_per_game=payload.innings_per_game,
        pa_qualifier_factor=payload.pa_qualifier_factor,
        ip_qualifier_factor=payload.ip_qualifier_factor,
        is_current=payload.is_current,
    )
    db.add(season)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError(422, "invalid season data", "invalid_input") from exc
    db.refresh(season)
    return season
