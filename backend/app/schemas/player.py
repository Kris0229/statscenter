from datetime import date

from pydantic import BaseModel


class PlayerOut(BaseModel):
    id: int
    team_id: int
    user_id: int | None
    name: str
    number: int
    positions: str | None
    bats: str | None
    throws: str | None
    photo_url: str | None
    title: str  # 'manager' | 'coach' | 'captain' | 'member'
    birthdate: date | None
    email: str | None
    phone: str | None
    status: str

    model_config = {"from_attributes": True}


class PlayerDetailOut(PlayerOut):
    """Admin-only, fetched on demand — carries the sensitive national_id field
    that PlayerOut deliberately omits from list/roster responses."""

    national_id: str | None


class PlayerCreate(BaseModel):
    name: str
    number: int
    positions: str | None = None
    bats: str | None = None
    throws: str | None = None
    user_id: int | None = None
    title: str | None = None  # 'manager' | 'coach' | 'captain' | 'member', defaults to 'member'
    birthdate: date | None = None
    national_id: str | None = None
    email: str | None = None
    phone: str | None = None


class PlayerPhotoUpdate(BaseModel):
    photo_url: str


class PlayerAccountCreate(BaseModel):
    email: str
    password: str
