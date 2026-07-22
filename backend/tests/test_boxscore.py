from datetime import date

from app.models import BattingLine, Game, Player, Season, Team
from tests.conftest import auth_headers, make_league, make_user
from tests.rtba_sample import build_rtba_game


def _enter_and_finalize(client, fixture) -> None:
    admin = fixture["admin"]
    game_id = fixture["game"].id
    for team_key, payload_key in (
        ("home_team", "home_batting_payload"), ("away_team", "away_batting_payload"),
    ):
        resp = client.put(
            f"/api/v1/games/{game_id}/batting",
            json={"team_id": fixture[team_key].id, "lines": fixture[payload_key]},
            headers=auth_headers(admin),
        )
        assert resp.status_code == 200, resp.text
    for team_key, payload_key in (
        ("home_team", "home_pitching_payload"), ("away_team", "away_pitching_payload"),
    ):
        resp = client.put(
            f"/api/v1/games/{game_id}/pitching",
            json={"team_id": fixture[team_key].id, "lines": fixture[payload_key]},
            headers=auth_headers(admin),
        )
        assert resp.status_code == 200, resp.text
    resp = client.patch(
        f"/api/v1/games/{game_id}", json={"line_score": fixture["line_score"]}, headers=auth_headers(admin),
    )
    assert resp.status_code == 200, resp.text
    resp = client.post(f"/api/v1/games/{game_id}/finalize", headers=auth_headers(admin))
    assert resp.status_code == 200, resp.text


def test_rtba_boxscore_totals_match_line_score_and_win_goes_to_away_pitcher(
    client, db_session,
) -> None:
    fixture = build_rtba_game(db_session, "Box")
    _enter_and_finalize(client, fixture)
    game_id = fixture["game"].id
    admin = fixture["admin"]

    resp = client.get(f"/api/v1/games/{game_id}/boxscore", headers=auth_headers(admin))
    assert resp.status_code == 200
    body = resp.json()

    assert body["game"]["code"] == "G6"
    assert body["game"]["status"] == "final"

    # totals reconcile with the batting lines / line_score
    assert body["line_score"]["home_totals"] == {"r": 3, "h": 9, "e": 1}
    assert body["line_score"]["away_totals"] == {"r": 5, "h": 11, "e": 0}
    assert body["line_score"]["home"] == fixture["line_score"]["home"]
    assert body["line_score"]["away"] == fixture["line_score"]["away"]

    # W goes to 李耀明 (away pitcher)
    away_pitching = body["away"]["pitching"]
    assert len(away_pitching) == 1
    assert away_pitching[0]["name"] == "李耀明"
    assert away_pitching[0]["decision"] == "W"
    assert away_pitching[0]["ip"] == "7.0"
    assert away_pitching[0]["era"] == "3.00"

    home_pitching = body["home"]["pitching"]
    assert home_pitching[0]["decision"] == "L"
    assert home_pitching[0]["era"] == "5.00"

    # batting notes: 巨人4 hit the only home HR, 運動家3 the only away HR
    assert "巨人4" in body["home"]["batting_notes"]["HR"]
    assert "巨人先發" in body["home"]["batting_notes"]["2B"]
    assert "運動家3" in body["away"]["batting_notes"]["HR"]
    assert "李耀明" in body["away"]["batting_notes"]["2B"]
    assert body["home"]["batting_notes"]["SB"] == []

    # every batting row carries a running AVG string
    for row in body["home"]["batting"] + body["away"]["batting"]:
        assert isinstance(row["avg"], str)


def test_boxscore_batting_avg_is_running_as_of_that_game(client, db_session) -> None:
    league = make_league(db_session, name="Boxscore Running", slug="boxscore-running")
    admin = make_user(db_session, email="admin@boxscore-running.test", role="admin", league_id=league.id)
    season = Season(league_id=league.id, year=2026, name="2026", innings_per_game=7)
    home = Team(league_id=league.id, name="Home")
    away = Team(league_id=league.id, name="Away")
    db_session.add_all([season, home, away])
    db_session.flush()
    batter = Player(league_id=league.id, team_id=home.id, name="Runner", number=1)
    db_session.add(batter)
    db_session.flush()

    g1 = Game(
        league_id=league.id, season_id=season.id, game_date=date(2026, 4, 1),
        home_team_id=home.id, away_team_id=away.id, status="final",
        line_score={"home": [1], "away": [0], "home_e": 0, "away_e": 0},
    )
    g2 = Game(
        league_id=league.id, season_id=season.id, game_date=date(2026, 4, 2),
        home_team_id=home.id, away_team_id=away.id, status="final",
        line_score={"home": [0], "away": [0], "home_e": 0, "away_e": 0},
    )
    db_session.add_all([g1, g2])
    db_session.flush()
    db_session.add_all([
        BattingLine(game_id=g1.id, player_id=batter.id, pa=4, ab=4, h=4, r=1),  # 1.000 through g1
        BattingLine(game_id=g2.id, player_id=batter.id, pa=4, ab=4, h=0, r=0),  # .500 through g2
    ])
    db_session.flush()

    resp1 = client.get(f"/api/v1/games/{g1.id}/boxscore", headers=auth_headers(admin))
    resp2 = client.get(f"/api/v1/games/{g2.id}/boxscore", headers=auth_headers(admin))

    row1 = next(r for r in resp1.json()["home"]["batting"] if r["player_id"] == batter.id)
    row2 = next(r for r in resp2.json()["home"]["batting"] if r["player_id"] == batter.id)
    assert row1["avg"] == "1.000"
    assert row2["avg"] == ".500"


def test_boxscore_cross_tenant_is_404(client, db_session) -> None:
    fixture_a = build_rtba_game(db_session, "BoxA")
    fixture_b = build_rtba_game(db_session, "BoxB")

    resp = client.get(
        f"/api/v1/games/{fixture_b['game'].id}/boxscore", headers=auth_headers(fixture_a["admin"]),
    )
    assert resp.status_code == 404


def test_boxscore_accessible_to_power_and_user_roles(client, db_session) -> None:
    fixture = build_rtba_game(db_session, "BoxRoles")
    _enter_and_finalize(client, fixture)
    league = fixture["league"]
    power = make_user(db_session, email="power@boxroles.test", role="power", league_id=league.id)
    user = make_user(db_session, email="user@boxroles.test", role="user", league_id=league.id)

    for account in (power, user):
        resp = client.get(
            f"/api/v1/games/{fixture['game'].id}/boxscore", headers=auth_headers(account),
        )
        assert resp.status_code == 200
