from pydantic import BaseModel


class BattingLeaderboardRow(BaseModel):
    player_id: int
    team_id: int
    name: str
    g: int
    pa: int
    ab: int
    h: int
    hr: int
    rbi: int
    bb: int
    so: int
