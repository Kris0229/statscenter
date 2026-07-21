from pydantic import BaseModel


class ValidateCheck(BaseModel):
    name: str
    ok: bool
    detail: str


class ValidateResult(BaseModel):
    ok: bool
    checks: list[ValidateCheck]
