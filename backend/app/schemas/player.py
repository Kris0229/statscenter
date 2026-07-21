from pydantic import BaseModel


class PlayerOut(BaseModel):
    id: int
    team_id: int
    name: str
    number: int
    positions: str | None
    bats: str | None
    throws: str | None
    photo_url: str | None
    status: str

    model_config = {"from_attributes": True}
