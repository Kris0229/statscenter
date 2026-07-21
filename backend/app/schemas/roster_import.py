from pydantic import BaseModel


class ImportRowError(BaseModel):
    row: int
    field: str
    msg: str


class ImportResult(BaseModel):
    valid_rows: int
    errors: list[ImportRowError]
    committed: bool
