"""Teams, roster (manual add + photo), tenant-scoped throughout.

Excel roster import/template and the roster-change-request workflow live in
their own modules (app/api/roster_import.py, app/api/roster_requests.py).
"""
from fastapi import APIRouter, Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_league_id, get_current_user, require_role
from app.core.errors import ApiError
from app.core.security import hash_password
from app.db.session import get_db
from app.models import Player, Team, User
from app.schemas.player import PlayerAccountCreate, PlayerCreate, PlayerOut, PlayerPhotoUpdate
from app.schemas.team import TeamCaptainCreate, TeamCreate, TeamOut, TeamUpdate
from app.schemas.user import UserOut

router = APIRouter(tags=["teams"])

_require_admin = require_role("admin")


def _get_team_or_404(db: Session, team_id: int, league_id: int) -> Team:
    team = db.query(Team).filter(Team.id == team_id, Team.league_id == league_id).one_or_none()
    if team is None:
        raise ApiError(404, "team not found", "not_found")
    return team


@router.get("/teams", response_model=list[TeamOut])
def list_teams(
    db: Session = Depends(get_db),
    league_id: int = Depends(get_current_league_id),
) -> list[Team]:
    return db.query(Team).filter(Team.league_id == league_id).order_by(Team.id).all()


@router.post("/teams", response_model=TeamOut, status_code=201)
def create_team(
    payload: TeamCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(_require_admin),
    league_id: int = Depends(get_current_league_id),
) -> Team:
    if payload.captain_user_id is not None:
        captain = db.get(User, payload.captain_user_id)
        if captain is None or captain.league_id != league_id:
            raise ApiError(404, "captain_user_id not found in this league", "not_found")

    team = Team(
        league_id=league_id, name=payload.name, logo_url=payload.logo_url,
        captain_user_id=payload.captain_user_id,
    )
    db.add(team)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError(409, "a team with that name already exists in this league", "conflict") from exc
    db.refresh(team)
    return team


@router.get("/teams/{team_id}", response_model=TeamOut)
def get_team(
    team_id: int,
    db: Session = Depends(get_db),
    league_id: int = Depends(get_current_league_id),
) -> Team:
    return _get_team_or_404(db, team_id, league_id)


@router.patch("/teams/{team_id}", response_model=TeamOut)
def update_team(
    team_id: int,
    payload: TeamUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(_require_admin),
    league_id: int = Depends(get_current_league_id),
) -> Team:
    team = _get_team_or_404(db, team_id, league_id)

    updates = payload.model_dump(exclude_unset=True)
    if updates.get("captain_user_id") is not None:
        captain = db.get(User, updates["captain_user_id"])
        if captain is None or captain.league_id != league_id:
            raise ApiError(404, "captain_user_id not found in this league", "not_found")
    for field, value in updates.items():
        setattr(team, field, value)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError(409, "a team with that name already exists in this league", "conflict") from exc
    db.refresh(team)
    return team


@router.post("/teams/{team_id}/captain-account", response_model=UserOut, status_code=201)
def create_team_captain_account(
    team_id: int,
    payload: TeamCaptainCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(_require_admin),
    league_id: int = Depends(get_current_league_id),
) -> User:
    """Create a `power`-role login for a team's captain and link it via
    `team.captain_user_id`. A separate, explicit step from roster import —
    the roster's `title` column is descriptive only, never auto-provisions
    a login (see BUILD_SPEC gap discussion)."""
    team = _get_team_or_404(db, team_id, league_id)
    if team.captain_user_id is not None:
        raise ApiError(409, "team already has a captain account", "conflict")

    captain = User(
        league_id=league_id, email=payload.email,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name, role="power",
    )
    db.add(captain)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError(409, "a user with that email already exists", "conflict") from exc

    team.captain_user_id = captain.id
    db.commit()
    db.refresh(captain)
    return captain


@router.post("/players/{player_id}/account", response_model=UserOut, status_code=201)
def create_player_account(
    player_id: int,
    payload: PlayerAccountCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(_require_admin),
    league_id: int = Depends(get_current_league_id),
) -> User:
    """Create a `user`-role login for a player and link it via `player.user_id`."""
    player = (
        db.query(Player).filter(Player.id == player_id, Player.league_id == league_id).one_or_none()
    )
    if player is None:
        raise ApiError(404, "player not found", "not_found")
    if player.user_id is not None:
        raise ApiError(409, "player already has an account", "conflict")

    account = User(
        league_id=league_id, email=payload.email,
        password_hash=hash_password(payload.password),
        display_name=player.name, role="user",
    )
    db.add(account)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError(409, "a user with that email already exists", "conflict") from exc

    player.user_id = account.id
    db.commit()
    db.refresh(account)
    return account


@router.get("/teams/{team_id}/players", response_model=list[PlayerOut])
def list_team_players(
    team_id: int,
    db: Session = Depends(get_db),
    league_id: int = Depends(get_current_league_id),
) -> list[Player]:
    team = _get_team_or_404(db, team_id, league_id)
    return db.query(Player).filter(Player.team_id == team.id).order_by(Player.number).all()


@router.post("/teams/{team_id}/players", response_model=PlayerOut, status_code=201)
def add_player(
    team_id: int,
    payload: PlayerCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(_require_admin),
    league_id: int = Depends(get_current_league_id),
) -> Player:
    team = _get_team_or_404(db, team_id, league_id)

    if payload.user_id is not None:
        linked_user = db.get(User, payload.user_id)
        if linked_user is None or linked_user.league_id != league_id:
            raise ApiError(404, "user_id not found in this league", "not_found")

    player = Player(
        league_id=league_id, team_id=team.id, user_id=payload.user_id,
        name=payload.name, number=payload.number, positions=payload.positions,
        bats=payload.bats, throws=payload.throws,
        title=payload.title or "member", birthdate=payload.birthdate,
        national_id=payload.national_id, email=payload.email, phone=payload.phone,
    )
    db.add(player)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError(
            409, "invalid or duplicate player data (number/bats/throws)", "conflict",
        ) from exc
    db.refresh(player)
    return player


@router.patch("/players/{player_id}/photo", response_model=PlayerOut)
def update_player_photo(
    player_id: int,
    payload: PlayerPhotoUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    league_id: int = Depends(get_current_league_id),
) -> Player:
    player = (
        db.query(Player)
        .filter(Player.id == player_id, Player.league_id == league_id)
        .one_or_none()
    )
    if player is None:
        raise ApiError(404, "player not found", "not_found")

    is_owner = user.role == "user" and player.user_id == user.id
    is_admin = user.role == "admin"
    if not (is_owner or is_admin):
        raise ApiError(403, "not allowed to update this player's photo", "forbidden")

    player.photo_url = payload.photo_url
    db.commit()
    db.refresh(player)
    return player
