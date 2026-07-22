from datetime import datetime

from pydantic import BaseModel


class MediaOut(BaseModel):
    id: int
    game_id: int | None
    player_id: int | None
    uploader_id: int
    type: str
    url: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MediaStatusUpdate(BaseModel):
    status: str  # 'active' | 'inactive'
