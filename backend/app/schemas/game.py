from datetime import date, datetime, time

from pydantic import BaseModel


class GameOut(BaseModel):
    id: int
    season_id: int
    game_date: date
    start_time: time | None
    venue: str | None
    game_type: str
    home_team_id: int
    away_team_id: int
    status: str
    line_score: dict | None
    code: str | None
    finalized_at: datetime | None

    model_config = {"from_attributes": True}


class GameCreate(BaseModel):
    season_id: int
    game_date: date
    start_time: time | None = None
    venue: str | None = None
    game_type: str = "regular"
    home_team_id: int
    away_team_id: int
    code: str | None = None


class GameUpdate(BaseModel):
    line_score: dict | None = None
    status: str | None = None  # 'scheduled'|'in_progress'|'postponed'|'cancelled' — not 'final', use /finalize
    venue: str | None = None
    start_time: time | None = None
    game_type: str | None = None
    code: str | None = None
