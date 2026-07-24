from fastapi import APIRouter, Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.core.errors import ApiError
from app.core.security import hash_password
from app.db.session import get_db
from app.models import League, User
from app.schemas.league import (
    LeagueAdminBootstrapRequest,
    LeagueAdminOut,
    LeagueCreate,
    LeagueOut,
    LeagueUpdate,
)

router = APIRouter(prefix="/admin/leagues", tags=["admin"])

_require_super_admin = require_role("super_admin")


def _get_league_or_404(db: Session, league_id: int) -> League:
    league = db.get(League, league_id)
    if league is None:
        raise ApiError(404, "league not found", "not_found")
    return league


@router.get("", response_model=list[LeagueOut])
def list_leagues(
    db: Session = Depends(get_db),
    _: User = Depends(_require_super_admin),
) -> list[League]:
    return db.query(League).order_by(League.id).all()


@router.post("", response_model=LeagueOut, status_code=201)
def create_league(
    payload: LeagueCreate,
    db: Session = Depends(get_db),
    _: User = Depends(_require_super_admin),
) -> League:
    league = League(name=payload.name, slug=payload.slug, logo_url=payload.logo_url)
    db.add(league)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError(409, "a league with that slug already exists", "conflict") from exc
    db.refresh(league)
    return league


@router.patch("/{league_id}", response_model=LeagueOut)
def update_league(
    league_id: int,
    payload: LeagueUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(_require_super_admin),
) -> League:
    league = _get_league_or_404(db, league_id)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(league, field, value)
    db.commit()
    db.refresh(league)
    return league


@router.get("/{league_id}/admins", response_model=list[LeagueAdminOut])
def list_league_admins(
    league_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(_require_super_admin),
) -> list[User]:
    _get_league_or_404(db, league_id)
    return (
        db.query(User)
        .filter(User.league_id == league_id, User.role == "admin")
        .order_by(User.id)
        .all()
    )


@router.post("/{league_id}/admins", response_model=LeagueAdminOut, status_code=201)
def bootstrap_league_admin(
    league_id: int,
    payload: LeagueAdminBootstrapRequest,
    db: Session = Depends(get_db),
    _: User = Depends(_require_super_admin),
) -> User:
    _get_league_or_404(db, league_id)

    admin = User(
        league_id=league_id,
        email=payload.email,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
        role="admin",
    )
    db.add(admin)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError(409, "a user with that email already exists", "conflict") from exc
    db.refresh(admin)
    return admin
