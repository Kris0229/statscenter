from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.core.security import TokenError, decode_token
from app.db.session import get_db
from app.models import User

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise ApiError(401, "not authenticated", "unauthenticated")
    try:
        payload = decode_token(credentials.credentials, expected_type="access")
    except TokenError as exc:
        raise ApiError(401, "invalid or expired token", "invalid_token") from exc

    user = db.get(User, int(payload["sub"]))
    if user is None or user.status != "active":
        raise ApiError(401, "user not found or inactive", "invalid_token")
    return user


def require_role(*roles: str):
    """Dependency factory: 403s unless the caller's role is one of `roles`."""

    def _dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise ApiError(403, "insufficient permissions", "forbidden")
        return user

    return _dependency


def get_current_league_id(user: User = Depends(get_current_user)) -> int:
    """Derive the tenant scope from the token — never from client input.

    super_admin carries no league_id and is rejected here: per §2 it does not
    do day-to-day league operations, so no league-scoped route is exposed to it.
    """
    if user.role == "super_admin" or user.league_id is None:
        raise ApiError(403, "super_admin has no league scope", "forbidden")
    return user.league_id
