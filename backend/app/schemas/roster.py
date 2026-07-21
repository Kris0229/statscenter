from datetime import datetime

from pydantic import BaseModel


class RosterChangeRequestCreate(BaseModel):
    type: str  # 'rename' | 'renumber' | 'add' | 'remove'
    payload: dict


class RosterChangeRequestOut(BaseModel):
    id: int
    team_id: int
    type: str
    payload: dict
    status: str
    reason: str | None
    requested_by: int
    reviewed_by: int | None
    created_at: datetime
    reviewed_at: datetime | None

    model_config = {"from_attributes": True}


class RosterChangeRequestReject(BaseModel):
    reason: str
