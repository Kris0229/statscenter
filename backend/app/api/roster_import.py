"""GET template.xlsx / POST roster import (BUILD_SPEC §5, admin only)."""
import io

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_league_id, require_role
from app.core.errors import ApiError
from app.db.session import get_db
from app.models import Player, Team, User
from app.schemas.roster_import import ImportResult, ImportRowError
from app.services.roster_import import build_template_workbook, parse_roster_workbook

router = APIRouter(tags=["roster-import"])

_require_admin = require_role("admin")


def _get_team_or_404(db: Session, team_id: int, league_id: int) -> Team:
    team = db.query(Team).filter(Team.id == team_id, Team.league_id == league_id).one_or_none()
    if team is None:
        raise ApiError(404, "team not found", "not_found")
    return team


@router.get("/teams/{team_id}/roster/template.xlsx")
def download_roster_template(
    team_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(_require_admin),
    league_id: int = Depends(get_current_league_id),
) -> StreamingResponse:
    _get_team_or_404(db, team_id, league_id)

    buf = io.BytesIO()
    build_template_workbook().save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=roster_template.xlsx"},
    )


@router.post("/teams/{team_id}/roster/import", response_model=ImportResult)
def import_roster(
    team_id: int,
    file: UploadFile = File(...),
    mode: str = Query("append", pattern="^(append|replace)$"),
    confirm: bool = Query(False),
    db: Session = Depends(get_db),
    admin: User = Depends(_require_admin),
    league_id: int = Depends(get_current_league_id),
) -> ImportResult:
    team = _get_team_or_404(db, team_id, league_id)

    parsed = parse_roster_workbook(file.file.read())
    errors = [ImportRowError(row=e.row, field=e.field, msg=e.msg) for e in parsed.errors]

    if mode == "append" and not errors:
        existing_numbers = {
            n
            for (n,) in db.query(Player.number).filter(
                Player.team_id == team.id, Player.status == "active",
            )
        }
        for r in parsed.valid_rows:
            if r.number in existing_numbers:
                errors.append(
                    ImportRowError(
                        row=r.row, field="number",
                        msg=f"number {r.number} is already active on this team",
                    ),
                )

    if errors:
        return ImportResult(valid_rows=len(parsed.valid_rows), errors=errors, committed=False)

    if mode == "replace" and not confirm:
        return ImportResult(valid_rows=len(parsed.valid_rows), errors=[], committed=False)

    if mode == "replace":
        db.query(Player).filter(
            Player.team_id == team.id, Player.status == "active",
        ).update({"status": "left"}, synchronize_session=False)

    for r in parsed.valid_rows:
        db.add(
            Player(
                league_id=league_id, team_id=team.id, name=r.name, number=r.number,
                positions=r.positions, bats=r.bats, throws=r.throws, title=r.title,
                birthdate=r.birthdate, national_id=r.national_id, email=r.email, phone=r.phone,
            ),
        )
    db.commit()

    return ImportResult(valid_rows=len(parsed.valid_rows), errors=[], committed=True)
