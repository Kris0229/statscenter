from decimal import Decimal

from pydantic import BaseModel


class SeasonCreate(BaseModel):
    year: int
    name: str
    innings_per_game: int = 7
    pa_qualifier_factor: Decimal = Decimal("2.00")
    ip_qualifier_factor: Decimal = Decimal("1.00")
    is_current: bool = False


class SeasonOut(BaseModel):
    id: int
    year: int
    name: str
    innings_per_game: int
    pa_qualifier_factor: Decimal
    ip_qualifier_factor: Decimal
    is_current: bool

    model_config = {"from_attributes": True}
