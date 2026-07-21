from pydantic import BaseModel


class PitchingLineIn(BaseModel):
    player_id: int
    seq: int = 1
    decision: str = "none"
    outs: int = 0
    np: int = 0
    bf: int = 0
    ab: int = 0
    h: int = 0
    hr: int = 0
    bb: int = 0
    hp: int = 0
    so: int = 0
    r: int = 0
    er: int = 0
    wp: int = 0
    gs: bool = False
    cg: bool = False
    sho: bool = False
    sv: bool = False
    svo: bool = False


class PitchingLineOut(PitchingLineIn):
    id: int
    game_id: int

    model_config = {"from_attributes": True}


class PitchingLinesUpsert(BaseModel):
    team_id: int
    lines: list[PitchingLineIn]
