from pydantic import BaseModel


class TeamOut(BaseModel):
    id: int
    name: str
    logo_url: str | None
    status: str

    model_config = {"from_attributes": True}
