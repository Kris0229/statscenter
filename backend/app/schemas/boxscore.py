from pydantic import BaseModel


class BoxscoreOut(BaseModel):
    game: dict
    line_score: dict
    home: dict
    away: dict
