from datetime import datetime

from pydantic import BaseModel


class LeagueCreate(BaseModel):
    name: str
    slug: str
    logo_url: str | None = None


class LeagueUpdate(BaseModel):
    name: str | None = None
    logo_url: str | None = None
    status: str | None = None  # 'active' | 'inactive'


class LeagueOut(BaseModel):
    id: int
    name: str
    slug: str
    logo_url: str | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class LeagueAdminBootstrapRequest(BaseModel):
    email: str
    display_name: str
    password: str


class LeagueAdminOut(BaseModel):
    id: int
    email: str
    display_name: str
    role: str
    league_id: int

    model_config = {"from_attributes": True}
