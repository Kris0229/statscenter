from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.core.security import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.db.session import get_db
from app.models import User
from app.schemas.auth import AccessTokenResponse, LoginRequest, RefreshRequest, TokenResponse

router = APIRouter(tags=["auth"])


@router.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.email == payload.email).one_or_none()
    if (
        user is None
        or user.status != "active"
        or not verify_password(payload.password, user.password_hash)
    ):
        raise ApiError(401, "invalid email or password", "invalid_credentials")

    return TokenResponse(
        access_token=create_access_token(user_id=user.id, role=user.role, league_id=user.league_id),
        refresh_token=create_refresh_token(user_id=user.id, role=user.role, league_id=user.league_id),
    )


@router.post("/auth/refresh", response_model=AccessTokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> AccessTokenResponse:
    try:
        claims = decode_token(payload.refresh_token, expected_type="refresh")
    except TokenError as exc:
        raise ApiError(401, "invalid or expired refresh token", "invalid_token") from exc

    user = db.get(User, int(claims["sub"]))
    if user is None or user.status != "active":
        raise ApiError(401, "user not found or inactive", "invalid_token")

    return AccessTokenResponse(
        access_token=create_access_token(user_id=user.id, role=user.role, league_id=user.league_id),
    )
