from app.models import Season
from tests.conftest import auth_headers, make_league, make_user


def test_list_seasons_tenant_scoped(client, db_session) -> None:
    league_a = make_league(db_session, name="Seasons A", slug="seasons-a")
    league_b = make_league(db_session, name="Seasons B", slug="seasons-b")
    admin_a = make_user(db_session, email="admin@seasons-a.test", role="admin", league_id=league_a.id)
    db_session.add_all([
        Season(league_id=league_a.id, year=2025, name="2025"),
        Season(league_id=league_a.id, year=2026, name="2026", is_current=True),
        Season(league_id=league_b.id, year=2026, name="2026 (other league)"),
    ])
    db_session.flush()

    resp = client.get("/api/v1/seasons", headers=auth_headers(admin_a))
    assert resp.status_code == 200
    body = resp.json()
    assert {row["year"] for row in body} == {2025, 2026}
    current = next(row for row in body if row["is_current"])
    assert current["year"] == 2026


def test_admin_creates_season(client, db_session) -> None:
    league = make_league(db_session, name="Seasons C", slug="seasons-c")
    admin = make_user(db_session, email="admin@seasons-c.test", role="admin", league_id=league.id)

    resp = client.post(
        "/api/v1/seasons",
        json={"year": 2026, "name": "2026 球季"},
        headers=auth_headers(admin),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["year"] == 2026
    assert body["innings_per_game"] == 7
    assert body["is_current"] is False


def test_creating_current_season_unsets_previous_current(client, db_session) -> None:
    league = make_league(db_session, name="Seasons D", slug="seasons-d")
    admin = make_user(db_session, email="admin@seasons-d.test", role="admin", league_id=league.id)
    old = Season(league_id=league.id, year=2025, name="2025", is_current=True)
    db_session.add(old)
    db_session.flush()

    resp = client.post(
        "/api/v1/seasons",
        json={"year": 2026, "name": "2026", "is_current": True},
        headers=auth_headers(admin),
    )
    assert resp.status_code == 201

    db_session.refresh(old)
    assert old.is_current is False


def test_power_cannot_create_season(client, db_session) -> None:
    league = make_league(db_session, name="Seasons E", slug="seasons-e")
    power = make_user(db_session, email="power@seasons-e.test", role="power", league_id=league.id)

    resp = client.post(
        "/api/v1/seasons", json={"year": 2026, "name": "2026"}, headers=auth_headers(power),
    )
    assert resp.status_code == 403
