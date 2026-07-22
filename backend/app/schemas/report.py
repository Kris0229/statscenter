from datetime import datetime

from pydantic import BaseModel


class ReportCreate(BaseModel):
    game_id: int
    title: str | None = None
    content: str | None = None
    cover_media_id: int | None = None


class ReportUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    cover_media_id: int | None = None


class ReportOut(BaseModel):
    id: int
    game_id: int
    title: str
    content: str | None
    cover_media_id: int | None
    author_id: int
    published_at: datetime | None

    model_config = {"from_attributes": True}


class ReportHighlights(BaseModel):
    home_team_name: str
    away_team_name: str
    home_score: int
    away_score: int
    winning_pitcher: str | None
    losing_pitcher: str | None
    save_pitcher: str | None
    home_runs: list[dict]
    multi_hit_batters: list[dict]
    big_strikeout_pitchers: list[dict]
