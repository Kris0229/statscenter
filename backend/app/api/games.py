"""Games, score entry, validation, and finalize (BUILD_SPEC §6.3, Phase 3)."""
from datetime import date, datetime, time, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_league_id, require_role
from app.core.errors import ApiError
from app.db.session import get_db
from app.models import AuditLog, BattingLine, Game, PitchingLine, Player, Season, Team, User
from app.schemas.batting import BattingLineOut, BattingLinesUpsert
from app.schemas.boxscore import BoxscoreOut
from app.schemas.game import GameCreate, GameOut, GameUpdate
from app.schemas.pitching import PitchingLineOut, PitchingLinesUpsert
from app.schemas.validate import ValidateCheck, ValidateResult
from app.services.boxscore import build_boxscore
from app.services.game_validation import overall_ok, run_validation_checks
from app.services.materialized_views import refresh_leaderboard_views

router = APIRouter(tags=["games"])

_require_admin = require_role("admin")


def _json_safe(value: object) -> object:
    if isinstance(value, (date, time, datetime)):
        return value.isoformat()
    return value


def _json_safe_dict(d: dict) -> dict:
    return {k: _json_safe(v) for k, v in d.items()}


def _get_game_or_404(db: Session, game_id: int, league_id: int) -> Game:
    game = db.query(Game).filter(Game.id == game_id, Game.league_id == league_id).one_or_none()
    if game is None:
        raise ApiError(404, "game not found", "not_found")
    return game


@router.get("/games", response_model=list[GameOut])
def list_games(
    season_id: int | None = Query(None),
    team_id: int | None = Query(None),
    status: str | None = Query(None),
    db: Session = Depends(get_db),
    league_id: int = Depends(get_current_league_id),
) -> list[Game]:
    query = db.query(Game).filter(Game.league_id == league_id)
    if season_id is not None:
        query = query.filter(Game.season_id == season_id)
    if team_id is not None:
        query = query.filter((Game.home_team_id == team_id) | (Game.away_team_id == team_id))
    if status is not None:
        query = query.filter(Game.status == status)
    return query.order_by(Game.id).all()


@router.post("/games", response_model=GameOut, status_code=201)
def create_game(
    payload: GameCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(_require_admin),
    league_id: int = Depends(get_current_league_id),
) -> Game:
    season = db.query(Season).filter(
        Season.id == payload.season_id, Season.league_id == league_id,
    ).one_or_none()
    if season is None:
        raise ApiError(404, "season not found", "not_found")

    for label, team_id in (("home_team_id", payload.home_team_id), ("away_team_id", payload.away_team_id)):
        team = db.query(Team).filter(Team.id == team_id, Team.league_id == league_id).one_or_none()
        if team is None:
            raise ApiError(404, f"{label} not found", "not_found")

    if payload.home_team_id == payload.away_team_id:
        raise ApiError(422, "home_team_id and away_team_id must differ", "invalid_input")

    game = Game(
        league_id=league_id, season_id=payload.season_id, game_date=payload.game_date,
        start_time=payload.start_time, venue=payload.venue, game_type=payload.game_type,
        home_team_id=payload.home_team_id, away_team_id=payload.away_team_id, code=payload.code,
    )
    db.add(game)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError(422, "invalid game data", "invalid_input") from exc
    db.refresh(game)
    return game


@router.get("/games/{game_id}", response_model=GameOut)
def get_game(
    game_id: int,
    db: Session = Depends(get_db),
    league_id: int = Depends(get_current_league_id),
) -> Game:
    return _get_game_or_404(db, game_id, league_id)


@router.patch("/games/{game_id}", response_model=GameOut)
def update_game(
    game_id: int,
    payload: GameUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(_require_admin),
    league_id: int = Depends(get_current_league_id),
) -> Game:
    game = _get_game_or_404(db, game_id, league_id)

    updates = payload.model_dump(exclude_unset=True)
    if updates.get("status") == "final":
        raise ApiError(422, "use POST /games/{id}/finalize to mark a game final", "invalid_input")

    if game.status == "final" and updates:
        before = _json_safe_dict({field: getattr(game, field) for field in updates})
        db.add(
            AuditLog(
                entity="game", entity_id=game.id, action="post_finalize_edit",
                before=before, after=_json_safe_dict(updates), actor_id=admin.id,
            ),
        )

    for field, value in updates.items():
        setattr(game, field, value)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError(422, "invalid game data", "invalid_input") from exc
    db.refresh(game)
    return game


def _team_player_ids(db: Session, team_id: int) -> set[int]:
    return {pid for (pid,) in db.query(Player.id).filter(Player.team_id == team_id)}


_BATTING_SNAPSHOT_FIELDS = [
    "player_id", "bat_order", "sub_index", "pos", "pa", "ab", "sh", "sf", "bb", "hp", "io",
    "tie", "r", "h", "b2", "b3", "hr", "rbi", "so", "sb", "cs", "gidp", "e",
]
_PITCHING_SNAPSHOT_FIELDS = [
    "player_id", "seq", "decision", "outs", "np", "bf", "ab", "h", "hr", "bb", "hp", "so",
    "r", "er", "wp", "gs", "cg", "sho", "sv", "svo",
]


def _snapshot_lines(lines: list, fields: list[str]) -> list[dict]:
    return [{f: getattr(line, f) for f in fields} for line in lines]


@router.get("/games/{game_id}/batting", response_model=list[BattingLineOut])
def get_batting_lines(
    game_id: int,
    db: Session = Depends(get_db),
    league_id: int = Depends(get_current_league_id),
) -> list[BattingLine]:
    """All batting lines for the game (both teams) — read-back for the
    score-entry UI (Phase 6) to re-hydrate its grid, e.g. after a reload.
    """
    game = _get_game_or_404(db, game_id, league_id)
    return (
        db.query(BattingLine)
        .filter(BattingLine.game_id == game.id)
        .order_by(BattingLine.bat_order, BattingLine.sub_index)
        .all()
    )


@router.get("/games/{game_id}/pitching", response_model=list[PitchingLineOut])
def get_pitching_lines(
    game_id: int,
    db: Session = Depends(get_db),
    league_id: int = Depends(get_current_league_id),
) -> list[PitchingLine]:
    game = _get_game_or_404(db, game_id, league_id)
    return (
        db.query(PitchingLine)
        .filter(PitchingLine.game_id == game.id)
        .order_by(PitchingLine.seq)
        .all()
    )


@router.put("/games/{game_id}/batting", response_model=list[BattingLineOut])
def put_batting_lines(
    game_id: int,
    payload: BattingLinesUpsert,
    db: Session = Depends(get_db),
    admin: User = Depends(_require_admin),
    league_id: int = Depends(get_current_league_id),
) -> list[BattingLine]:
    game = _get_game_or_404(db, game_id, league_id)
    if payload.team_id not in (game.home_team_id, game.away_team_id):
        raise ApiError(422, "team_id must be the game's home or away team", "invalid_input")

    roster_ids = _team_player_ids(db, payload.team_id)
    bad = {line.player_id for line in payload.lines} - roster_ids
    if bad:
        raise ApiError(422, f"player_id(s) not on team {payload.team_id}: {sorted(bad)}", "invalid_input")

    existing_lines = db.query(BattingLine).filter(
        BattingLine.game_id == game_id, BattingLine.player_id.in_(roster_ids),
    ).all()
    before_snapshot = (
        _snapshot_lines(existing_lines, _BATTING_SNAPSHOT_FIELDS) if game.status == "final" else None
    )

    db.query(BattingLine).filter(
        BattingLine.game_id == game_id, BattingLine.player_id.in_(roster_ids),
    ).delete(synchronize_session=False)

    new_lines = [BattingLine(game_id=game_id, **line.model_dump()) for line in payload.lines]
    db.add_all(new_lines)

    if before_snapshot is not None:
        db.flush()
        db.add(
            AuditLog(
                entity="game", entity_id=game.id, action="post_finalize_batting_edit",
                before={"team_id": payload.team_id, "lines": before_snapshot},
                after={"team_id": payload.team_id, "lines": _snapshot_lines(new_lines, _BATTING_SNAPSHOT_FIELDS)},
                actor_id=admin.id,
            ),
        )

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError(422, "invalid batting line data (check constraints failed)", "invalid_input") from exc
    for line in new_lines:
        db.refresh(line)
    return new_lines


@router.put("/games/{game_id}/pitching", response_model=list[PitchingLineOut])
def put_pitching_lines(
    game_id: int,
    payload: PitchingLinesUpsert,
    db: Session = Depends(get_db),
    admin: User = Depends(_require_admin),
    league_id: int = Depends(get_current_league_id),
) -> list[PitchingLine]:
    game = _get_game_or_404(db, game_id, league_id)
    if payload.team_id not in (game.home_team_id, game.away_team_id):
        raise ApiError(422, "team_id must be the game's home or away team", "invalid_input")

    roster_ids = _team_player_ids(db, payload.team_id)
    bad = {line.player_id for line in payload.lines} - roster_ids
    if bad:
        raise ApiError(422, f"player_id(s) not on team {payload.team_id}: {sorted(bad)}", "invalid_input")

    existing_lines = db.query(PitchingLine).filter(
        PitchingLine.game_id == game_id, PitchingLine.player_id.in_(roster_ids),
    ).all()
    before_snapshot = (
        _snapshot_lines(existing_lines, _PITCHING_SNAPSHOT_FIELDS) if game.status == "final" else None
    )

    db.query(PitchingLine).filter(
        PitchingLine.game_id == game_id, PitchingLine.player_id.in_(roster_ids),
    ).delete(synchronize_session=False)

    new_lines = [PitchingLine(game_id=game_id, **line.model_dump()) for line in payload.lines]
    db.add_all(new_lines)

    if before_snapshot is not None:
        db.flush()
        db.add(
            AuditLog(
                entity="game", entity_id=game.id, action="post_finalize_pitching_edit",
                before={"team_id": payload.team_id, "lines": before_snapshot},
                after={"team_id": payload.team_id, "lines": _snapshot_lines(new_lines, _PITCHING_SNAPSHOT_FIELDS)},
                actor_id=admin.id,
            ),
        )

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError(422, "invalid pitching line data (check constraints failed)", "invalid_input") from exc
    for line in new_lines:
        db.refresh(line)
    return new_lines


@router.post("/games/{game_id}/validate", response_model=ValidateResult)
def validate_game(
    game_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(_require_admin),
    league_id: int = Depends(get_current_league_id),
) -> ValidateResult:
    game = _get_game_or_404(db, game_id, league_id)
    checks = run_validation_checks(db, game)
    return ValidateResult(
        ok=overall_ok(checks),
        checks=[ValidateCheck(name=c.name, ok=c.ok, detail=c.detail) for c in checks],
    )


@router.post("/games/{game_id}/finalize", response_model=GameOut)
def finalize_game(
    game_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(_require_admin),
    league_id: int = Depends(get_current_league_id),
) -> Game:
    game = _get_game_or_404(db, game_id, league_id)
    if game.status == "final":
        raise ApiError(409, "game is already final", "conflict")

    checks = run_validation_checks(db, game)
    if not overall_ok(checks):
        failing = [c.name for c in checks if c.blocking and not c.ok]
        raise ApiError(409, f"validation failed: {failing}", "validation_failed")

    before_status = game.status
    game.status = "final"
    game.finalized_at = datetime.now(timezone.utc)
    db.add(
        AuditLog(
            entity="game", entity_id=game.id, action="finalize",
            before={"status": before_status}, after={"status": "final"}, actor_id=admin.id,
        ),
    )
    refresh_leaderboard_views(db)
    db.commit()
    db.refresh(game)
    return game


@router.get("/games/{game_id}/boxscore", response_model=BoxscoreOut)
def get_boxscore(
    game_id: int,
    db: Session = Depends(get_db),
    league_id: int = Depends(get_current_league_id),
) -> dict:
    # Read-only and available to every league role (admin/power/user) per §2 —
    # unlike score entry/finalize, viewing a boxscore isn't admin-only.
    game = _get_game_or_404(db, game_id, league_id)
    return build_boxscore(db, game)
