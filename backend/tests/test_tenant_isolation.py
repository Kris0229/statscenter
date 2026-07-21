from app.models import BattingLine, Game, Player, Season, Team
from tests.conftest import auth_headers, make_league, make_user


def _make_full_league(db_session, suffix: str) -> dict:
    league = make_league(db_session, name=f"League {suffix}", slug=f"league-{suffix.lower()}")
    admin = make_user(
        db_session, email=f"admin@league-{suffix.lower()}.test", role="admin",
        league_id=league.id,
    )
    season = Season(league_id=league.id, year=2026, name="2026")
    home = Team(league_id=league.id, name=f"{suffix} Home")
    away = Team(league_id=league.id, name=f"{suffix} Away")
    db_session.add_all([season, home, away])
    db_session.flush()

    player = Player(league_id=league.id, team_id=home.id, name=f"{suffix} Player", number=1)
    db_session.add(player)
    db_session.flush()

    game = Game(
        league_id=league.id, season_id=season.id, game_date="2026-04-01",
        home_team_id=home.id, away_team_id=away.id, status="final",
    )
    db_session.add(game)
    db_session.flush()

    batting = BattingLine(game_id=game.id, player_id=player.id, pa=4, ab=4, h=2, hr=1)
    db_session.add(batting)
    db_session.flush()

    return {
        "league": league, "admin": admin, "season": season,
        "home": home, "away": away, "player": player, "game": game,
    }


def test_cross_tenant_team_read_is_404_not_403(client, db_session) -> None:
    league_a = _make_full_league(db_session, "A")
    league_b = _make_full_league(db_session, "B")

    resp = client.get(
        f"/api/v1/teams/{league_b['home'].id}", headers=auth_headers(league_a["admin"]),
    )
    assert resp.status_code == 404


def test_cross_tenant_game_read_is_404_not_403(client, db_session) -> None:
    league_a = _make_full_league(db_session, "A")
    league_b = _make_full_league(db_session, "B")

    resp = client.get(
        f"/api/v1/games/{league_b['game'].id}", headers=auth_headers(league_a["admin"]),
    )
    assert resp.status_code == 404


def test_teams_list_ignores_forged_league_id_query_param(client, db_session) -> None:
    league_a = _make_full_league(db_session, "A")
    league_b = _make_full_league(db_session, "B")

    resp = client.get(
        f"/api/v1/teams?league_id={league_b['league'].id}",
        headers=auth_headers(league_a["admin"]),
    )
    assert resp.status_code == 200
    names = {row["name"] for row in resp.json()}
    assert names == {"A Home", "A Away"}


def test_team_players_list_ignores_forged_league_id_query_param(client, db_session) -> None:
    league_a = _make_full_league(db_session, "A")
    league_b = _make_full_league(db_session, "B")

    resp = client.get(
        f"/api/v1/teams/{league_a['home'].id}/players?league_id={league_b['league'].id}",
        headers=auth_headers(league_a["admin"]),
    )
    assert resp.status_code == 200
    names = {row["name"] for row in resp.json()}
    assert names == {"A Player"}

    cross_resp = client.get(
        f"/api/v1/teams/{league_b['home'].id}/players", headers=auth_headers(league_a["admin"]),
    )
    assert cross_resp.status_code == 404


def test_games_list_ignores_forged_league_id_query_param(client, db_session) -> None:
    league_a = _make_full_league(db_session, "A")
    league_b = _make_full_league(db_session, "B")

    resp = client.get(
        f"/api/v1/games?league_id={league_b['league'].id}",
        headers=auth_headers(league_a["admin"]),
    )
    assert resp.status_code == 200
    game_ids = {row["id"] for row in resp.json()}
    assert game_ids == {league_a["game"].id}


def test_leaderboard_ignores_forged_league_id_query_param(client, db_session) -> None:
    league_a = _make_full_league(db_session, "A")
    league_b = _make_full_league(db_session, "B")

    resp = client.get(
        f"/api/v1/leaderboards/batting?league_id={league_b['league'].id}",
        headers=auth_headers(league_a["admin"]),
    )
    assert resp.status_code == 200
    player_ids = {row["player_id"] for row in resp.json()}
    assert player_ids == {league_a["player"].id}


def test_super_admin_has_no_access_to_league_scoped_routers(client, db_session) -> None:
    super_admin = make_user(
        db_session, email="super@statscenter.test", role="super_admin", league_id=None,
    )

    for path in ("/api/v1/teams", "/api/v1/games", "/api/v1/leaderboards/batting"):
        resp = client.get(path, headers=auth_headers(super_admin))
        assert resp.status_code == 403, path
