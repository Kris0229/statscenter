from app.models import Player, Team
from tests.conftest import auth_headers, make_league, make_user


def _setup(db_session, suffix: str):
    league = make_league(db_session, name=f"Photo {suffix}", slug=f"photo-{suffix.lower()}")
    admin = make_user(
        db_session, email=f"admin@photo-{suffix.lower()}.test", role="admin",
        league_id=league.id,
    )
    owner = make_user(
        db_session, email=f"owner@photo-{suffix.lower()}.test", role="user",
        league_id=league.id,
    )
    other_user = make_user(
        db_session, email=f"other@photo-{suffix.lower()}.test", role="user",
        league_id=league.id,
    )
    team = Team(league_id=league.id, name=f"{suffix} Team")
    db_session.add(team)
    db_session.flush()
    player = Player(
        league_id=league.id, team_id=team.id, user_id=owner.id, name="Owner Player", number=3,
    )
    db_session.add(player)
    db_session.flush()
    return league, admin, owner, other_user, player


def test_user_can_update_own_player_photo(client, db_session) -> None:
    _, _admin, owner, _other, player = _setup(db_session, "A")

    resp = client.patch(
        f"/api/v1/players/{player.id}/photo",
        json={"photo_url": "https://example.com/me.jpg"},
        headers=auth_headers(owner),
    )
    assert resp.status_code == 200
    assert resp.json()["photo_url"] == "https://example.com/me.jpg"


def test_user_cannot_update_another_players_photo(client, db_session) -> None:
    _, _admin, _owner, other_user, player = _setup(db_session, "B")

    resp = client.patch(
        f"/api/v1/players/{player.id}/photo",
        json={"photo_url": "https://example.com/hacked.jpg"},
        headers=auth_headers(other_user),
    )
    assert resp.status_code == 403


def test_admin_can_update_any_players_photo_in_league(client, db_session) -> None:
    _, admin, _owner, _other, player = _setup(db_session, "C")

    resp = client.patch(
        f"/api/v1/players/{player.id}/photo",
        json={"photo_url": "https://example.com/admin-set.jpg"},
        headers=auth_headers(admin),
    )
    assert resp.status_code == 200


def test_cross_tenant_photo_update_is_404(client, db_session) -> None:
    _, _admin_a, _owner_a, _other_a, player_a = _setup(db_session, "D")
    _, admin_b, _owner_b, _other_b, _player_b = _setup(db_session, "E")

    resp = client.patch(
        f"/api/v1/players/{player_a.id}/photo",
        json={"photo_url": "https://example.com/cross.jpg"},
        headers=auth_headers(admin_b),
    )
    assert resp.status_code == 404


def test_power_cannot_update_player_photo(client, db_session) -> None:
    league, _admin, _owner, _other, player = _setup(db_session, "F")
    power = make_user(db_session, email="power@photo-f.test", role="power", league_id=league.id)

    resp = client.patch(
        f"/api/v1/players/{player.id}/photo",
        json={"photo_url": "https://example.com/power.jpg"},
        headers=auth_headers(power),
    )
    assert resp.status_code == 403
