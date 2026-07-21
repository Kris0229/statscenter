from datetime import date

from pydantic import BaseModel


class CareerStats(BaseModel):
    batting: dict
    pitching: dict


class SeasonStatLine(BaseModel):
    season_id: int
    season_name: str
    season_year: int
    batting: dict | None
    pitching: dict | None


class GamelogEntry(BaseModel):
    game_id: int
    game_date: date
    code: str | None
    season_id: int
    opponent_team_id: int
    is_home: bool
    batting: dict | None
    pitching: list[dict] | None


class PlayerStatsOut(BaseModel):
    career: CareerStats
    per_season: list[SeasonStatLine]
    gamelog: list[GamelogEntry]
