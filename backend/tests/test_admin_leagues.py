from app.core.security import decode_token
from tests.conftest import auth_headers, make_league, make_user


def _make_super_admin(db_session):
    return make_user(
        db_session, email="super@statscenter.test", role="super_admin", league_id=None,
    )


def test_super_admin_creates_league_and_bootstraps_admin_who_can_log_in(
    client, db_session,
) -> None:
    super_admin = _make_super_admin(db_session)

    create_resp = client.post(
        "/api/v1/admin/leagues",
        json={"name": "League B", "slug": "league-b"},
        headers=auth_headers(super_admin),
    )
    assert create_resp.status_code == 201
    league_b = create_resp.json()
    assert league_b["slug"] == "league-b"

    bootstrap_resp = client.post(
        f"/api/v1/admin/leagues/{league_b['id']}/admins",
        json={
            "email": "admin@league-b.test",
            "display_name": "League B Admin",
            "password": "LeagueB-Pass1!",
        },
        headers=auth_headers(super_admin),
    )
    assert bootstrap_resp.status_code == 201
    assert bootstrap_resp.json()["league_id"] == league_b["id"]

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@league-b.test", "password": "LeagueB-Pass1!"},
    )
    assert login_resp.status_code == 200
    claims = decode_token(login_resp.json()["access_token"], expected_type="access")
    assert claims["role"] == "admin"
    assert claims["league_id"] == league_b["id"]


def test_league_admin_cannot_access_admin_leagues_router(client, db_session) -> None:
    league_a = make_league(db_session, name="League A", slug="league-a")
    admin_a = make_user(
        db_session, email="admin@league-a.test", role="admin", league_id=league_a.id,
    )

    resp = client.get("/api/v1/admin/leagues", headers=auth_headers(admin_a))
    assert resp.status_code == 403
    assert resp.json()["code"] == "forbidden"


def test_super_admin_can_suspend_a_league(client, db_session) -> None:
    super_admin = _make_super_admin(db_session)
    league = make_league(db_session, name="Suspend Me", slug="suspend-me")

    resp = client.patch(
        f"/api/v1/admin/leagues/{league.id}",
        json={"status": "inactive"},
        headers=auth_headers(super_admin),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "inactive"

    list_resp = client.get("/api/v1/admin/leagues", headers=auth_headers(super_admin))
    body_by_id = {row["id"]: row for row in list_resp.json()}
    assert body_by_id[league.id]["status"] == "inactive"


def test_bootstrap_admin_for_nonexistent_league_is_404(client, db_session) -> None:
    super_admin = _make_super_admin(db_session)

    resp = client.post(
        "/api/v1/admin/leagues/999999/admins",
        json={"email": "ghost@nowhere.test", "display_name": "Ghost", "password": "x"},
        headers=auth_headers(super_admin),
    )
    assert resp.status_code == 404


def test_create_league_duplicate_slug_is_409(client, db_session) -> None:
    super_admin = _make_super_admin(db_session)
    make_league(db_session, name="Existing", slug="dup-slug")

    resp = client.post(
        "/api/v1/admin/leagues",
        json={"name": "Duplicate", "slug": "dup-slug"},
        headers=auth_headers(super_admin),
    )
    assert resp.status_code == 409
