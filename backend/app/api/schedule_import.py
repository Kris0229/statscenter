"""GET template.xlsx / POST schedule (fixture list) import, admin only.

Same dry-run-then-confirm shape as app/api/roster_import.py — parse errors
(and a first commit attempt with confirm=False) are returned as data
(200 + `committed: false`), not HTTP errors.
"""
import io

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_league_id, require_role
from app.core.errors import ApiError
from app.db.session import get_db
from app.models import Game, Season, Team, User
from app.schemas.roster_import import ImportResult, ImportRowError
from app.services.schedule_import import build_template_workbook, parse_schedule_workbook

router = APIRouter(tags=["schedule-import"])

_require_admin = require_role("admin")


def _get_season_or_404(db: Session, season_id: int, league_id: int) -> Season:
    season = (
        db.query(Season).filter(Season.id == season_id, Season.league_id == league_id).one_or_none()
    )
    if season is None:
        raise ApiError(404, "season not found", "not_found")
    return season


@router.get("/seasons/{season_id}/games/template.xlsx")
def download_schedule_template(
    season_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(_require_admin),
    league_id: int = Depends(get_current_league_id),
) -> StreamingResponse:
    _get_season_or_404(db, season_id, league_id)

    buf = io.BytesIO()
    build_template_workbook().save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=schedule_template.xlsx"},
    )


@router.post("/seasons/{season_id}/games/import", response_model=ImportResult)
def import_schedule(
    season_id: int,
    file: UploadFile = File(...),
    confirm: bool = Query(False),
    db: Session = Depends(get_db),
    admin: User = Depends(_require_admin),
    league_id: int = Depends(get_current_league_id),
) -> ImportResult:
    season = _get_season_or_404(db, season_id, league_id)

    parsed = parse_schedule_workbook(file.file.read())
    errors = [ImportRowError(row=e.row, field=e.field, msg=e.msg) for e in parsed.errors]

    teams = db.query(Team).filter(Team.league_id == league_id).all()
    name_to_id = {t.name: t.id for t in teams}

    resolved: list[tuple] = []
    for r in parsed.valid_rows:
        away_id = name_to_id.get(r.away_team_name)
        home_id = name_to_id.get(r.home_team_name)
        if away_id is None:
            errors.append(
                ImportRowError(row=r.row, field="away_team", msg=f"team not found: {r.away_team_name!r}"),
            )
        if home_id is None:
            errors.append(
                ImportRowError(row=r.row, field="home_team", msg=f"team not found: {r.home_team_name!r}"),
            )
        if away_id is not None and home_id is not None:
            resolved.append((r, away_id, home_id))

    if errors:
        return ImportResult(valid_rows=len(parsed.valid_rows), errors=errors, committed=False)

    if not confirm:
        return ImportResult(valid_rows=len(resolved), errors=[], committed=False)

    for r, away_id, home_id in resolved:
        db.add(
            Game(
                league_id=league_id, season_id=season.id, game_date=r.game_date,
                start_time=r.start_time, venue=r.venue, home_team_id=home_id,
                away_team_id=away_id, code=r.match_no,
            ),
        )
    db.commit()

    return ImportResult(valid_rows=len(resolved), errors=[], committed=True)
