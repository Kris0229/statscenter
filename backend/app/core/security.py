from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _pwd_context.verify(password, password_hash)


class TokenError(Exception):
    """Raised for any invalid, expired, or wrong-type JWT."""


def _create_token(
    *, user_id: int, role: str, league_id: int | None, ttl_seconds: int, token_type: str,
) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "league_id": league_id,
        "type": token_type,
        "iat": now,
        "exp": now + timedelta(seconds=ttl_seconds),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def create_access_token(*, user_id: int, role: str, league_id: int | None) -> str:
    settings = get_settings()
    return _create_token(
        user_id=user_id, role=role, league_id=league_id,
        ttl_seconds=settings.JWT_ACCESS_TTL, token_type="access",
    )


def create_refresh_token(*, user_id: int, role: str, league_id: int | None) -> str:
    settings = get_settings()
    return _create_token(
        user_id=user_id, role=role, league_id=league_id,
        ttl_seconds=settings.JWT_REFRESH_TTL, token_type="refresh",
    )


def decode_token(token: str, *, expected_type: str) -> dict:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    except JWTError as exc:
        raise TokenError(str(exc)) from exc
    if payload.get("type") != expected_type:
        raise TokenError(f"expected a {expected_type} token, got {payload.get('type')!r}")
    return payload
