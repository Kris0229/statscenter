from pydantic import BaseModel


class TeamOut(BaseModel):
    id: int
    name: str
    logo_url: str | None
    status: str

    model_config = {"from_attributes": True}


class TeamCreate(BaseModel):
    name: str
    logo_url: str | None = None
    captain_user_id: int | None = None


class TeamUpdate(BaseModel):
    name: str | None = None
    logo_url: str | None = None
    captain_user_id: int | None = None
    status: str | None = None  # 'active' | 'inactive'
