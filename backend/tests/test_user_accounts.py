from app.models import Player, Team, User
from tests.conftest import auth_headers, make_league, make_user


def _setup(db_session, suffix: str):
    league = make_league(db_session, name=f"Accts {suffix}", slug=f"accts-{suffix.lower()}")
    admin = make_user(
        db_session, email=f"admin@accts-{suffix.lower()}.test", role="admin",
        league_id=league.id,
    )
    team = Team(league_id=league.id, name=f"{suffix} Team")
    db_session.add(team)
    db_session.flush()
    player = Player(league_id=league.id, team_id=team.id, name="Roster Player", number=4)
    db_session.add(player)
    db_session.flush()
    return league, admin, team, player


def test_admin_creates_team_captain_account(client, db_session) -> None:
    _, admin, team, _player = _setup(db_session, "A")

    resp = client.post(
        f"/api/v1/teams/{team.id}/captain-account",
        json={"email": "captain@accts-a.test", "password": "pw123456", "display_name": "Captain"},
        headers=auth_headers(admin),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["role"] == "power"
    assert body["email"] == "captain@accts-a.test"

    db_session.refresh(team)
    created = db_session.query(User).filter(User.email == "captain@accts-a.test").one()
    assert team.captain_user_id == created.id


def test_cannot_create_second_captain_account(client, db_session) -> None:
    _, admin, team, _player = _setup(db_session, "B")
    payload = {"email": "captain1@accts-b.test", "password": "pw123456", "display_name": "C1"}
    first = client.post(f"/api/v1/teams/{team.id}/captain-account", json=payload, headers=auth_headers(admin))
    assert first.status_code == 201

    second = client.post(
        f"/api/v1/teams/{team.id}/captain-account",
        json={"email": "captain2@accts-b.test", "password": "pw123456", "display_name": "C2"},
        headers=auth_headers(admin),
    )
    assert second.status_code == 409


def test_admin_creates_player_account(client, db_session) -> None:
    _, admin, _team, player = _setup(db_session, "C")

    resp = client.post(
        f"/api/v1/players/{player.id}/account",
        json={"email": "player@accts-c.test", "password": "pw123456"},
        headers=auth_headers(admin),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["role"] == "user"
    assert body["display_name"] == "Roster Player"

    db_session.refresh(player)
    created = db_session.query(User).filter(User.email == "player@accts-c.test").one()
    assert player.user_id == created.id


def test_cannot_create_second_player_account(client, db_session) -> None:
    _, admin, _team, player = _setup(db_session, "D")
    payload = {"email": "p1@accts-d.test", "password": "pw123456"}
    first = client.post(f"/api/v1/players/{player.id}/account", json=payload, headers=auth_headers(admin))
    assert first.status_code == 201

    second = client.post(
        f"/api/v1/players/{player.id}/account",
        json={"email": "p2@accts-d.test", "password": "pw123456"},
        headers=auth_headers(admin),
    )
    assert second.status_code == 409


def test_duplicate_email_across_accounts_is_conflict(client, db_session) -> None:
    league, admin, team, player = _setup(db_session, "E")
    make_user(db_session, email="taken@accts-e.test", role="user", league_id=league.id)

    resp = client.post(
        f"/api/v1/teams/{team.id}/captain-account",
        json={"email": "taken@accts-e.test", "password": "pw123456", "display_name": "Dup"},
        headers=auth_headers(admin),
    )
    assert resp.status_code == 409


def test_power_cannot_create_accounts(client, db_session) -> None:
    league, _admin, team, player = _setup(db_session, "F")
    power = make_user(db_session, email="power@accts-f.test", role="power", league_id=league.id)

    resp = client.post(
        f"/api/v1/teams/{team.id}/captain-account",
        json={"email": "x@accts-f.test", "password": "pw123456", "display_name": "X"},
        headers=auth_headers(power),
    )
    assert resp.status_code == 403

    resp2 = client.post(
        f"/api/v1/players/{player.id}/account",
        json={"email": "y@accts-f.test", "password": "pw123456"},
        headers=auth_headers(power),
    )
    assert resp2.status_code == 403
