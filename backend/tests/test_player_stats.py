from app.models import BattingLine, Game, Player, Season, Team
from app.services.materialized_views import refresh_leaderboard_views
from tests.conftest import auth_headers, make_league, make_user


def _setup(db_session, suffix: str):
    league = make_league(db_session, name=f"PS {suffix}", slug=f"ps-{suffix.lower()}")
    admin = make_user(db_session, email=f"admin@ps-{suffix.lower()}.test", role="admin", league_id=league.id)
    season = Season(league_id=league.id, year=2026, name="2026", is_current=True)
    home = Team(league_id=league.id, name=f"{suffix} Home")
    away = Team(league_id=league.id, name=f"{suffix} Away")
    db_session.add_all([season, home, away])
    db_session.flush()
    player = Player(league_id=league.id, team_id=home.id, name="Star Player", number=1)
    db_session.add(player)
    db_session.flush()
    return league, admin, season, home, away, player


def test_gamelog_returns_one_row_per_finalized_game(client, db_session) -> None:
    league, admin, season, home, away, player = _setup(db_session, "Log")

    g1 = Game(
        league_id=league.id, season_id=season.id, game_date="2026-04-02",
        home_team_id=home.id, away_team_id=away.id, status="final",
    )
    g2 = Game(
        league_id=league.id, season_id=season.id, game_date="2026-04-01",
        home_team_id=home.id, away_team_id=away.id, status="final",
    )
    g3_not_final = Game(
        league_id=league.id, season_id=season.id, game_date="2026-04-03",
        home_team_id=home.id, away_team_id=away.id, status="scheduled",
    )
    db_session.add_all([g1, g2, g3_not_final])
    db_session.flush()

    db_session.add_all([
        BattingLine(game_id=g1.id, player_id=player.id, pa=4, ab=4, h=2, hr=1, r=1),
        BattingLine(game_id=g2.id, player_id=player.id, pa=4, ab=3, bb=1, h=1, r=0),
    ])
    db_session.flush()

    resp = client.get(f"/api/v1/players/{player.id}/gamelog", headers=auth_headers(admin))
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert [row["game_id"] for row in body] == [g2.id, g1.id]  # ordered by game_date
    assert body[1]["batting"]["h"] == 2
    assert body[1]["batting"]["avg"] == 0.5
    assert body[1]["pitching"] is None


def test_gamelog_season_filter(client, db_session) -> None:
    league, admin, season, home, away, player = _setup(db_session, "Filter")
    other_season = Season(league_id=league.id, year=2025, name="2025")
    db_session.add(other_season)
    db_session.flush()

    g_this = Game(
        league_id=league.id, season_id=season.id, game_date="2026-04-01",
        home_team_id=home.id, away_team_id=away.id, status="final",
    )
    g_other = Game(
        league_id=league.id, season_id=other_season.id, game_date="2025-04-01",
        home_team_id=home.id, away_team_id=away.id, status="final",
    )
    db_session.add_all([g_this, g_other])
    db_session.flush()
    db_session.add_all([
        BattingLine(game_id=g_this.id, player_id=player.id, pa=4, ab=4, h=1, r=0),
        BattingLine(game_id=g_other.id, player_id=player.id, pa=4, ab=4, h=1, r=0),
    ])
    db_session.flush()

    resp = client.get(
        f"/api/v1/players/{player.id}/gamelog?season_id={season.id}", headers=auth_headers(admin),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["game_id"] == g_this.id


def test_player_career_stats_match_hand_summed_totals(client, db_session) -> None:
    league, admin, season, home, away, player = _setup(db_session, "Career")

    g1 = Game(
        league_id=league.id, season_id=season.id, game_date="2026-04-01",
        home_team_id=home.id, away_team_id=away.id, status="final",
    )
    g2 = Game(
        league_id=league.id, season_id=season.id, game_date="2026-04-02",
        home_team_id=home.id, away_team_id=away.id, status="final",
    )
    db_session.add_all([g1, g2])
    db_session.flush()
    db_session.add_all([
        BattingLine(game_id=g1.id, player_id=player.id, pa=4, ab=4, h=2, hr=1, r=1),
        BattingLine(game_id=g2.id, player_id=player.id, pa=4, ab=4, h=1, hr=0, r=0),
    ])
    db_session.flush()
    refresh_leaderboard_views(db_session)
    db_session.flush()

    resp = client.get(f"/api/v1/players/{player.id}/stats", headers=auth_headers(admin))
    assert resp.status_code == 200
    body = resp.json()
    career_batting = body["career"]["batting"]
    assert career_batting["g"] == 2
    assert career_batting["pa"] == 8
    assert career_batting["ab"] == 8
    assert career_batting["h"] == 3
    assert career_batting["hr"] == 1
    assert career_batting["avg"] == 3 / 8

    assert len(body["per_season"]) == 1
    assert body["per_season"][0]["season_id"] == season.id
    assert body["per_season"][0]["batting"]["h"] == 3

    assert len(body["gamelog"]) == 2


def test_player_stats_cross_tenant_is_404(client, db_session) -> None:
    _league_a, admin_a, _season_a, _home_a, _away_a, _player_a = _setup(db_session, "TenA")
    _league_b, _admin_b, _season_b, _home_b, _away_b, player_b = _setup(db_session, "TenB")

    resp = client.get(f"/api/v1/players/{player_b.id}/stats", headers=auth_headers(admin_a))
    assert resp.status_code == 404
