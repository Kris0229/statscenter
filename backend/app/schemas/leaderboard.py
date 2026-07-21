from pydantic import BaseModel


class BattingLeaderboardRow(BaseModel):
    rank: int
    player_id: int
    player_name: str
    team_id: int
    qualified: bool
    g: int
    pa: int
    ab: int
    r: int
    h: int
    b2: int
    b3: int
    hr: int
    rbi: int
    bb: int
    hp: int
    sf: int
    sh: int
    so: int
    sb: int
    cs: int
    avg: float | None
    obp: float | None
    slg: float | None
    ops: float | None


class PitchingLeaderboardRow(BaseModel):
    rank: int
    player_id: int
    player_name: str
    team_id: int
    qualified: bool
    g: int
    gs: int
    w: int
    l: int  # noqa: E741 — matches the mv_pitching_season "l" (losses) column
    cg: int
    sho: int
    outs: int
    np: int
    bf: int
    ab: int
    h: int
    hr: int
    bb: int
    hp: int
    so: int
    r: int
    er: int
    era: float | None
    whip: float | None
    oppavg: float | None
