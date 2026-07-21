from pydantic import BaseModel


class BattingLineIn(BaseModel):
    player_id: int
    bat_order: int | None = None
    sub_index: int = 0
    pos: str | None = None
    pa: int = 0
    ab: int = 0
    sh: int = 0
    sf: int = 0
    bb: int = 0
    hp: int = 0
    io: int = 0
    tie: int = 0
    r: int = 0
    h: int = 0
    b2: int = 0
    b3: int = 0
    hr: int = 0
    rbi: int = 0
    so: int = 0
    sb: int = 0
    cs: int = 0
    gidp: int = 0
    e: int = 0


class BattingLineOut(BattingLineIn):
    id: int
    game_id: int

    model_config = {"from_attributes": True}


class BattingLinesUpsert(BaseModel):
    team_id: int
    lines: list[BattingLineIn]
