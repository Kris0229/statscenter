from app.models import Player, Team
from tests.conftest import auth_headers, make_league, make_user


def _setup(db_session, suffix: str):
    league = make_league(db_session, name=f"Detail {suffix}", slug=f"detail-{suffix.lower()}")
    admin = make_user(
        db_session, email=f"admin@detail-{suffix.lower()}.test", role="admin",
        league_id=league.id,
    )
    team = Team(league_id=league.id, name=f"{suffix} Team")
    db_session.add(team)
    db_session.flush()
    player = Player(
        league_id=league.id, team_id=team.id, name="Detail Player", number=7,
        national_id="B123456789",
    )
    db_session.add(player)
    db_session.flush()
    return league, admin, player


def test_admin_can_fetch_player_detail_with_national_id(client, db_session) -> None:
    _, admin, player = _setup(db_session, "A")

    resp = client.get(f"/api/v1/players/{player.id}", headers=auth_headers(admin))
    assert resp.status_code == 200
    assert resp.json()["national_id"] == "B123456789"


def test_power_cannot_fetch_player_detail(client, db_session) -> None:
    league, _admin, player = _setup(db_session, "B")
    power = make_user(db_session, email="power@detail-b.test", role="power", league_id=league.id)

    resp = client.get(f"/api/v1/players/{player.id}", headers=auth_headers(power))
    assert resp.status_code == 403


def test_cross_tenant_player_detail_is_404(client, db_session) -> None:
    _, _admin_a, player_a = _setup(db_session, "C")
    _, admin_b, _player_b = _setup(db_session, "D")

    resp = client.get(f"/api/v1/players/{player_a.id}", headers=auth_headers(admin_b))
    assert resp.status_code == 404
