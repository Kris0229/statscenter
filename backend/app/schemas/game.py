from datetime import date, time

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
    code: str | None

    model_config = {"from_attributes": True}
