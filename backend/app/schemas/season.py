from decimal import Decimal

from pydantic import BaseModel


class SeasonOut(BaseModel):
    id: int
    year: int
    name: str
    innings_per_game: int
    pa_qualifier_factor: Decimal
    ip_qualifier_factor: Decimal
    is_current: bool

    model_config = {"from_attributes": True}
