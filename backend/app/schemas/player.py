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


class PlayerCreate(BaseModel):
    name: str
    number: int
    positions: str | None = None
    bats: str | None = None
    throws: str | None = None
    user_id: int | None = None


class PlayerPhotoUpdate(BaseModel):
    photo_url: str
