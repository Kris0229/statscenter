from app.core.security import decode_token
from tests.conftest import make_league, make_user


def test_login_success_returns_tokens_with_correct_claims(client, db_session) -> None:
    league = make_league(db_session, name="Login League", slug="login-league")
    user = make_user(
        db_session, email="admin@login-league.test", role="admin",
        league_id=league.id, password="CorrectHorse1!",
    )

    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@login-league.test", "password": "CorrectHorse1!"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"

    access_claims = decode_token(body["access_token"], expected_type="access")
    assert access_claims["sub"] == str(user.id)
    assert access_claims["role"] == "admin"
    assert access_claims["league_id"] == league.id

    refresh_claims = decode_token(body["refresh_token"], expected_type="refresh")
    assert refresh_claims["sub"] == str(user.id)


def test_login_wrong_password_rejected(client, db_session) -> None:
    league = make_league(db_session, name="Bad PW League", slug="bad-pw-league")
    make_user(
        db_session, email="user@bad-pw-league.test", role="user",
        league_id=league.id, password="RightPass1!",
    )

    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "user@bad-pw-league.test", "password": "WrongPass1!"},
    )
    assert resp.status_code == 401
    assert resp.json()["code"] == "invalid_credentials"


def test_login_unknown_email_rejected(client) -> None:
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@nowhere.test", "password": "whatever"},
    )
    assert resp.status_code == 401
    assert resp.json()["code"] == "invalid_credentials"


def test_refresh_issues_new_access_token(client, db_session) -> None:
    league = make_league(db_session, name="Refresh League", slug="refresh-league")
    make_user(
        db_session, email="admin@refresh-league.test", role="admin",
        league_id=league.id, password="RefreshMe1!",
    )
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@refresh-league.test", "password": "RefreshMe1!"},
    )
    refresh_token = login_resp.json()["refresh_token"]

    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    new_access_token = resp.json()["access_token"]
    decode_token(new_access_token, expected_type="access")  # doesn't raise


def test_refresh_rejects_an_access_token(client, db_session) -> None:
    league = make_league(db_session, name="Refresh Reject League", slug="refresh-reject")
    make_user(
        db_session, email="admin@refresh-reject.test", role="admin",
        league_id=league.id, password="RefreshMe1!",
    )
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@refresh-reject.test", "password": "RefreshMe1!"},
    )
    access_token = login_resp.json()["access_token"]

    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": access_token})
    assert resp.status_code == 401


def test_protected_endpoint_requires_auth(client) -> None:
    resp = client.get("/api/v1/admin/leagues")
    assert resp.status_code == 401
