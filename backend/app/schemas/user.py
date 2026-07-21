from pydantic import BaseModel


class UserOut(BaseModel):
    id: int
    email: str
    display_name: str
    role: str
    league_id: int | None
    status: str

    model_config = {"from_attributes": True}
