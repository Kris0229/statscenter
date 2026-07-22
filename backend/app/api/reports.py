"""Admin report editor + publish (§7). Not in BUILD_SPEC §6's contract —
designed here following the rest of the API's tenant-scoping/role patterns.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_league_id, get_current_user, require_role
from app.core.errors import ApiError
from app.db.session import get_db
from app.models import Game, Report, User
from app.schemas.report import ReportCreate, ReportHighlights, ReportOut, ReportUpdate
from app.services.reports import build_report_highlights, default_report_title, render_auto_content

router = APIRouter(tags=["reports"])

_require_admin = require_role("admin")


def _get_game_or_404(db: Session, game_id: int, league_id: int) -> Game:
    game = db.query(Game).filter(Game.id == game_id, Game.league_id == league_id).one_or_none()
    if game is None:
        raise ApiError(404, "game not found", "not_found")
    return game


def _get_report_or_404(db: Session, report_id: int, league_id: int) -> Report:
    report = db.get(Report, report_id)
    if report is None:
        raise ApiError(404, "report not found", "not_found")
    game = db.get(Game, report.game_id)
    if game is None or game.league_id != league_id:
        raise ApiError(404, "report not found", "not_found")
    return report


@router.get("/games/{game_id}/report-highlights", response_model=ReportHighlights)
def get_report_highlights(
    game_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(_require_admin),
    league_id: int = Depends(get_current_league_id),
) -> dict:
    game = _get_game_or_404(db, game_id, league_id)
    return build_report_highlights(db, game)


@router.post("/reports", response_model=ReportOut, status_code=201)
def create_report(
    payload: ReportCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(_require_admin),
    league_id: int = Depends(get_current_league_id),
) -> Report:
    game = _get_game_or_404(db, payload.game_id, league_id)
    highlights = build_report_highlights(db, game)

    report = Report(
        game_id=game.id,
        title=payload.title or default_report_title(game, highlights),
        content=payload.content if payload.content is not None else render_auto_content(highlights),
        cover_media_id=payload.cover_media_id,
        author_id=admin.id,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@router.get("/reports", response_model=list[ReportOut])
def list_reports(
    game_id: int | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    league_id: int = Depends(get_current_league_id),
) -> list[Report]:
    query = (
        db.query(Report).join(Game, Game.id == Report.game_id).filter(Game.league_id == league_id)
    )
    if game_id is not None:
        query = query.filter(Report.game_id == game_id)
    if user.role != "admin":
        query = query.filter(Report.published_at.isnot(None))
    return query.order_by(Report.id.desc()).all()


@router.get("/reports/{report_id}", response_model=ReportOut)
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    league_id: int = Depends(get_current_league_id),
) -> Report:
    report = _get_report_or_404(db, report_id, league_id)
    if report.published_at is None and user.role != "admin":
        raise ApiError(404, "report not found", "not_found")
    return report


@router.patch("/reports/{report_id}", response_model=ReportOut)
def update_report(
    report_id: int,
    payload: ReportUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(_require_admin),
    league_id: int = Depends(get_current_league_id),
) -> Report:
    report = _get_report_or_404(db, report_id, league_id)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(report, field, value)
    db.commit()
    db.refresh(report)
    return report


@router.post("/reports/{report_id}/publish", response_model=ReportOut)
def publish_report(
    report_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(_require_admin),
    league_id: int = Depends(get_current_league_id),
) -> Report:
    report = _get_report_or_404(db, report_id, league_id)
    report.published_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(report)
    return report
