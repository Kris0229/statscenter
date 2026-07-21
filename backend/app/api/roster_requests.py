"""Roster change workflow (BUILD_SPEC §6.2): power requests, admin reviews."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_league_id, get_current_user, require_role
from app.core.errors import ApiError
from app.db.session import get_db
from app.models import AuditLog, Player, RosterChangeRequest, Team, User
from app.schemas.roster import (
    RosterChangeRequestCreate,
    RosterChangeRequestOut,
    RosterChangeRequestReject,
)

router = APIRouter(tags=["roster-requests"])

_require_power = require_role("power")
_require_admin = require_role("admin")
_REQUEST_TYPES = ("rename", "renumber", "add", "remove")


def _get_team_or_404(db: Session, team_id: int, league_id: int) -> Team:
    team = db.query(Team).filter(Team.id == team_id, Team.league_id == league_id).one_or_none()
    if team is None:
        raise ApiError(404, "team not found", "not_found")
    return team


def _get_request_or_404(db: Session, request_id: int, league_id: int) -> RosterChangeRequest:
    req = (
        db.query(RosterChangeRequest)
        .filter(RosterChangeRequest.id == request_id, RosterChangeRequest.league_id == league_id)
        .one_or_none()
    )
    if req is None:
        raise ApiError(404, "roster change request not found", "not_found")
    return req


def _require_payload_fields(payload: dict, *fields: str) -> None:
    missing = [f for f in fields if f not in payload]
    if missing:
        raise ApiError(422, f"payload missing fields: {missing}", "invalid_input")


def _get_player_or_404(db: Session, player_id: object, league_id: int) -> Player:
    player = (
        db.query(Player).filter(Player.id == player_id, Player.league_id == league_id).one_or_none()
    )
    if player is None:
        raise ApiError(404, "player not found", "not_found")
    return player


@router.post(
    "/teams/{team_id}/roster-requests", response_model=RosterChangeRequestOut, status_code=201,
)
def create_roster_request(
    team_id: int,
    payload: RosterChangeRequestCreate,
    db: Session = Depends(get_db),
    power: User = Depends(_require_power),
    league_id: int = Depends(get_current_league_id),
) -> RosterChangeRequest:
    team = _get_team_or_404(db, team_id, league_id)
    if team.captain_user_id != power.id:
        raise ApiError(403, "you are not the captain of this team", "forbidden")
    if payload.type not in _REQUEST_TYPES:
        raise ApiError(422, f"type must be one of {_REQUEST_TYPES}", "invalid_input")

    req = RosterChangeRequest(
        league_id=league_id, team_id=team.id, type=payload.type,
        payload=payload.payload, requested_by=power.id,
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


@router.get("/roster-requests", response_model=list[RosterChangeRequestOut])
def list_roster_requests(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    league_id: int = Depends(get_current_league_id),
) -> list[RosterChangeRequest]:
    query = db.query(RosterChangeRequest).filter(RosterChangeRequest.league_id == league_id)
    if user.role == "admin":
        pass
    elif user.role == "power":
        query = query.join(Team, Team.id == RosterChangeRequest.team_id).filter(
            Team.captain_user_id == user.id,
        )
    else:
        raise ApiError(403, "insufficient permissions", "forbidden")
    return query.order_by(RosterChangeRequest.id).all()


@router.post("/roster-requests/{request_id}/approve", response_model=RosterChangeRequestOut)
def approve_roster_request(
    request_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(_require_admin),
    league_id: int = Depends(get_current_league_id),
) -> RosterChangeRequest:
    req = _get_request_or_404(db, request_id, league_id)
    if req.status != "pending":
        raise ApiError(409, "request already reviewed", "conflict")

    before: dict | None = None
    after: dict | None = None
    entity_id: int | None = None

    if req.type == "rename":
        _require_payload_fields(req.payload, "player_id", "name")
        player = _get_player_or_404(db, req.payload["player_id"], league_id)
        before, after = {"name": player.name}, {"name": req.payload["name"]}
        player.name = req.payload["name"]
        entity_id = player.id
    elif req.type == "renumber":
        _require_payload_fields(req.payload, "player_id", "number")
        player = _get_player_or_404(db, req.payload["player_id"], league_id)
        before, after = {"number": player.number}, {"number": req.payload["number"]}
        player.number = req.payload["number"]
        entity_id = player.id
    elif req.type == "add":
        _require_payload_fields(req.payload, "name", "number")
        player = Player(
            league_id=league_id, team_id=req.team_id,
            name=req.payload["name"], number=req.payload["number"],
            positions=req.payload.get("positions"),
            bats=req.payload.get("bats"), throws=req.payload.get("throws"),
        )
        db.add(player)
        db.flush()
        after = {"name": player.name, "number": player.number}
        entity_id = player.id
    else:  # remove
        _require_payload_fields(req.payload, "player_id")
        player = _get_player_or_404(db, req.payload["player_id"], league_id)
        before, after = {"status": player.status}, {"status": "left"}
        player.status = "left"
        entity_id = player.id

    req.status = "approved"
    req.reviewed_by = admin.id
    req.reviewed_at = datetime.now(timezone.utc)
    db.add(
        AuditLog(
            entity="player", entity_id=entity_id, action=f"roster_request_{req.type}",
            before=before, after=after, actor_id=admin.id,
        ),
    )

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError(
            409, "approval would violate roster constraints (e.g. duplicate number)", "conflict",
        ) from exc
    db.refresh(req)
    return req


@router.post("/roster-requests/{request_id}/reject", response_model=RosterChangeRequestOut)
def reject_roster_request(
    request_id: int,
    payload: RosterChangeRequestReject,
    db: Session = Depends(get_db),
    admin: User = Depends(_require_admin),
    league_id: int = Depends(get_current_league_id),
) -> RosterChangeRequest:
    req = _get_request_or_404(db, request_id, league_id)
    if req.status != "pending":
        raise ApiError(409, "request already reviewed", "conflict")

    req.status = "rejected"
    req.reason = payload.reason
    req.reviewed_by = admin.id
    req.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(req)
    return req
