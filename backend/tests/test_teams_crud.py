from app.models import Team
from tests.conftest import auth_headers, make_league, make_user


def test_power_cannot_create_team(client, db_session) -> None:
    league = make_league(db_session, name="Crud League 1", slug="crud-league-1")
    power = make_user(db_session, email="power@crud-1.test", role="power", league_id=league.id)

    resp = client.post("/api/v1/teams", json={"name": "New Team"}, headers=auth_headers(power))
    assert resp.status_code == 403


def test_admin_can_create_team(client, db_session) -> None:
    league = make_league(db_session, name="Crud League 2", slug="crud-league-2")
    admin = make_user(db_session, email="admin@crud-2.test", role="admin", league_id=league.id)

    resp = client.post("/api/v1/teams", json={"name": "New Team"}, headers=auth_headers(admin))
    assert resp.status_code == 201
    assert resp.json()["name"] == "New Team"


def test_admin_cannot_patch_cross_tenant_team(client, db_session) -> None:
    league_a = make_league(db_session, name="Crud A", slug="crud-a")
    league_b = make_league(db_session, name="Crud B", slug="crud-b")
    admin_a = make_user(db_session, email="admin@crud-a.test", role="admin", league_id=league_a.id)
    team_b = Team(league_id=league_b.id, name="B Team")
    db_session.add(team_b)
    db_session.flush()

    resp = client.patch(
        f"/api/v1/teams/{team_b.id}", json={"name": "Hacked"}, headers=auth_headers(admin_a),
    )
    assert resp.status_code == 404


def test_create_team_with_captain_from_other_league_is_404(client, db_session) -> None:
    league_a = make_league(db_session, name="Crud A2", slug="crud-a2")
    league_b = make_league(db_session, name="Crud B2", slug="crud-b2")
    admin_a = make_user(db_session, email="admin@crud-a2.test", role="admin", league_id=league_a.id)
    outsider = make_user(
        db_session, email="outsider@crud-b2.test", role="power", league_id=league_b.id,
    )

    resp = client.post(
        "/api/v1/teams", json={"name": "Team X", "captain_user_id": outsider.id},
        headers=auth_headers(admin_a),
    )
    assert resp.status_code == 404
