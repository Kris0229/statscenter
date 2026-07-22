"""Media upload/list/hide/delete.

Not in BUILD_SPEC §6's contract listing — designed here following the same
tenant-scoping and role patterns as the rest of the API, per §7's prose
("associate to game/player", "admin can hide media; uploader can delete
own") and §8's "upload MIME whitelist".
"""
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_league_id, get_current_user, require_role
from app.core.config import get_settings
from app.core.errors import ApiError
from app.db.session import get_db
from app.models import Game, Media, Player, User
from app.schemas.media import MediaOut, MediaStatusUpdate
from app.services.storage import ALLOWED_PHOTO_MIME_TYPES, get_storage_backend

router = APIRouter(tags=["media"])

_require_admin = require_role("admin")
_UPLOAD_ROLES = ("admin", "power", "user")
_MEDIA_TYPES = ("photo", "video", "link")


def _check_game(db: Session, game_id: int, league_id: int) -> None:
    game = db.query(Game).filter(Game.id == game_id, Game.league_id == league_id).one_or_none()
    if game is None:
        raise ApiError(404, "game not found", "not_found")


def _check_player(db: Session, player_id: int, league_id: int) -> None:
    player = db.query(Player).filter(
        Player.id == player_id, Player.league_id == league_id,
    ).one_or_none()
    if player is None:
        raise ApiError(404, "player not found", "not_found")


def _get_media_or_404(db: Session, media_id: int, league_id: int) -> Media:
    media = db.get(Media, media_id)
    if media is None:
        raise ApiError(404, "media not found", "not_found")
    # media carries no league_id of its own — derive it via game/player.
    league = None
    if media.game_id is not None:
        game = db.get(Game, media.game_id)
        league = game.league_id if game else None
    elif media.player_id is not None:
        player = db.get(Player, media.player_id)
        league = player.league_id if player else None
    if league != league_id:
        raise ApiError(404, "media not found", "not_found")
    return media


@router.post("/media", response_model=MediaOut, status_code=201)
def upload_media(
    type: str = Form(...),  # noqa: A002 — matches the DB column/API field name
    game_id: int | None = Form(None),
    player_id: int | None = Form(None),
    url: str | None = Form(None),
    file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    league_id: int = Depends(get_current_league_id),
) -> Media:
    if user.role not in _UPLOAD_ROLES:
        raise ApiError(403, "insufficient permissions", "forbidden")
    if type not in _MEDIA_TYPES:
        raise ApiError(422, f"type must be one of {_MEDIA_TYPES}", "invalid_input")
    if game_id is None and player_id is None:
        raise ApiError(422, "game_id or player_id is required", "invalid_input")

    if game_id is not None:
        _check_game(db, game_id, league_id)
    if player_id is not None:
        _check_player(db, player_id, league_id)

    if type == "photo":
        if file is None:
            raise ApiError(422, "file is required for type=photo", "invalid_input")
        content_type = file.content_type or ""
        if content_type not in ALLOWED_PHOTO_MIME_TYPES:
            raise ApiError(
                422, f"unsupported image type: {content_type or 'unknown'}", "invalid_input",
            )
        content = file.file.read()
        if len(content) > get_settings().MEDIA_MAX_BYTES:
            raise ApiError(422, "file too large", "invalid_input")
        stored_url = get_storage_backend().save(
            filename=file.filename or "upload", content=content, content_type=content_type,
        )
    else:
        if not url:
            raise ApiError(422, f"url is required for type={type}", "invalid_input")
        stored_url = url

    media = Media(
        game_id=game_id, player_id=player_id, uploader_id=user.id, type=type, url=stored_url,
    )
    db.add(media)
    db.commit()
    db.refresh(media)
    return media


@router.get("/media", response_model=list[MediaOut])
def list_media(
    game_id: int | None = Query(None),
    player_id: int | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    league_id: int = Depends(get_current_league_id),
) -> list[Media]:
    if game_id is None and player_id is None:
        raise ApiError(422, "game_id or player_id query param is required", "invalid_input")

    query = db.query(Media)
    if game_id is not None:
        _check_game(db, game_id, league_id)
        query = query.filter(Media.game_id == game_id)
    if player_id is not None:
        _check_player(db, player_id, league_id)
        query = query.filter(Media.player_id == player_id)
    if user.role != "admin":
        query = query.filter(Media.status == "active")

    return query.order_by(Media.created_at.desc()).all()


@router.patch("/media/{media_id}", response_model=MediaOut)
def update_media_status(
    media_id: int,
    payload: MediaStatusUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(_require_admin),
    league_id: int = Depends(get_current_league_id),
) -> Media:
    media = _get_media_or_404(db, media_id, league_id)
    media.status = payload.status
    db.commit()
    db.refresh(media)
    return media


@router.delete("/media/{media_id}", status_code=204)
def delete_media(
    media_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    league_id: int = Depends(get_current_league_id),
) -> None:
    media = _get_media_or_404(db, media_id, league_id)
    if user.role != "admin" and media.uploader_id != user.id:
        raise ApiError(403, "only the uploader or an admin can delete this media", "forbidden")

    media_type, media_url = media.type, media.url
    db.delete(media)
    db.commit()

    if media_type == "photo":
        try:
            get_storage_backend().delete(media_url)
        except Exception:
            pass  # best-effort: the DB row is already gone either way
