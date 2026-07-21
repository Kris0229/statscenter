from app.models import BattingLine, Game, PitchingLine, Player, Season, Team
from app.services.materialized_views import refresh_leaderboard_views
from tests.conftest import auth_headers, make_league, make_user


def _setup_league(db_session, suffix: str):
    league = make_league(db_session, name=f"LB {suffix}", slug=f"lb-{suffix.lower()}")
    admin = make_user(db_session, email=f"admin@lb-{suffix.lower()}.test", role="admin", league_id=league.id)
    season = Season(league_id=league.id, year=2026, name="2026", is_current=True)
    home = Team(league_id=league.id, name=f"{suffix} Home")
    away = Team(league_id=league.id, name=f"{suffix} Away")
    db_session.add_all([season, home, away])
    db_session.flush()
    return league, admin, season, home, away


def _finalized_game(db_session, league, season, home, away, game_date: str) -> Game:
    game = Game(
        league_id=league.id, season_id=season.id, game_date=game_date,
        home_team_id=home.id, away_team_id=away.id, status="final",
    )
    db_session.add(game)
    db_session.flush()
    return game


def _build_batting_scenario(db_session, suffix: str):
    """2 finalized games between the same 2 teams -> team_games=2 each, so
    the default pa_qualifier_factor (2.00) needs PA>=4 to be qualified.
    p1: PA=8 h=3 hr=3 (qualified, avg=.375). p2: PA=8 h=2 hr=0 (qualified,
    avg=.250). p3: PA=1 h=1 hr=0 (unqualified, avg=1.000 — the small-sample
    outlier the qualifier filter exists to hide).
    """
    league, admin, season, home, away = _setup_league(db_session, suffix)
    p1 = Player(league_id=league.id, team_id=home.id, name="P1", number=1)
    p2 = Player(league_id=league.id, team_id=home.id, name="P2", number=2)
    p3 = Player(league_id=league.id, team_id=away.id, name="P3", number=3)
    db_session.add_all([p1, p2, p3])
    db_session.flush()

    g1 = _finalized_game(db_session, league, season, home, away, "2026-04-01")
    g2 = _finalized_game(db_session, league, season, home, away, "2026-04-02")

    db_session.add_all([
        BattingLine(game_id=g1.id, player_id=p1.id, pa=4, ab=4, h=2, hr=2, r=2),
        BattingLine(game_id=g1.id, player_id=p2.id, pa=4, ab=4, h=1, hr=0, r=0),
        BattingLine(game_id=g1.id, player_id=p3.id, pa=1, ab=1, h=1, hr=0, r=0),
        BattingLine(game_id=g2.id, player_id=p1.id, pa=4, ab=4, h=1, hr=1, r=1),
        BattingLine(game_id=g2.id, player_id=p2.id, pa=4, ab=4, h=1, hr=0, r=0),
    ])
    db_session.flush()
    refresh_leaderboard_views(db_session)
    db_session.flush()

    return {
        "league": league, "admin": admin, "season": season, "home": home, "away": away,
        "p1": p1, "p2": p2, "p3": p3,
    }


def test_batting_leaderboard_sort_hr_desc(client, db_session) -> None:
    fx = _build_batting_scenario(db_session, "HR")
    resp = client.get(
        "/api/v1/leaderboards/batting?sort=hr&order=desc&qualified=false",
        headers=auth_headers(fx["admin"]),
    )
    assert resp.status_code == 200
    body = resp.json()
    hrs = [row["hr"] for row in body]
    assert hrs == sorted(hrs, reverse=True)
    assert body[0]["player_id"] == fx["p1"].id
    assert body[0]["hr"] == 3


def test_batting_leaderboard_ties_share_rank(client, db_session) -> None:
    fx = _build_batting_scenario(db_session, "Tie")
    resp = client.get(
        "/api/v1/leaderboards/batting?sort=hr&order=desc&qualified=false",
        headers=auth_headers(fx["admin"]),
    )
    body = resp.json()
    by_player = {row["player_id"]: row for row in body}
    # p2 and p3 are both hr=0 -> tied for rank 2 (p1's hr=3 takes rank 1)
    assert by_player[fx["p1"].id]["rank"] == 1
    assert by_player[fx["p2"].id]["hr"] == 0
    assert by_player[fx["p3"].id]["hr"] == 0
    assert by_player[fx["p2"].id]["rank"] == by_player[fx["p3"].id]["rank"] == 2


def test_batting_leaderboard_order_flip(client, db_session) -> None:
    fx = _build_batting_scenario(db_session, "Flip")
    desc = client.get(
        "/api/v1/leaderboards/batting?sort=hr&order=desc&qualified=false",
        headers=auth_headers(fx["admin"]),
    ).json()
    asc = client.get(
        "/api/v1/leaderboards/batting?sort=hr&order=asc&qualified=false",
        headers=auth_headers(fx["admin"]),
    ).json()
    # Compare hr *values* (not player_id order) — with a tie at hr=0, a
    # stable sort legitimately preserves the tied pair's relative order in
    # both directions, so reversing player_id lists isn't a valid check.
    desc_values = [row["hr"] for row in desc]
    asc_values = [row["hr"] for row in asc]
    assert desc_values == list(reversed(asc_values))
    assert desc_values == sorted(desc_values, reverse=True)


def test_batting_leaderboard_qualified_filter_on_avg_sort(client, db_session) -> None:
    fx = _build_batting_scenario(db_session, "Qual")

    qualified_resp = client.get(
        "/api/v1/leaderboards/batting?sort=avg&order=desc&qualified=true",
        headers=auth_headers(fx["admin"]),
    )
    qualified_ids = {row["player_id"] for row in qualified_resp.json()}
    assert fx["p3"].id not in qualified_ids
    assert {fx["p1"].id, fx["p2"].id} <= qualified_ids

    unqualified_resp = client.get(
        "/api/v1/leaderboards/batting?sort=avg&order=desc&qualified=false",
        headers=auth_headers(fx["admin"]),
    )
    body = unqualified_resp.json()
    ids = {row["player_id"] for row in body}
    assert fx["p3"].id in ids
    # p3's small-sample 1.000 avg tops the list once qualification is ignored
    assert body[0]["player_id"] == fx["p3"].id
    assert body[0]["qualified"] is False


def test_pitching_leaderboard_sort_era_asc(client, db_session) -> None:
    league, admin, season, home, away = _setup_league(db_session, "Era")
    p_home = Player(league_id=league.id, team_id=home.id, name="HomeAce", number=1)
    p_away = Player(league_id=league.id, team_id=away.id, name="AwayAce", number=1)
    db_session.add_all([p_home, p_away])
    db_session.flush()

    g1 = _finalized_game(db_session, league, season, home, away, "2026-04-01")
    g2 = _finalized_game(db_session, league, season, home, away, "2026-04-02")

    db_session.add_all([
        PitchingLine(game_id=g1.id, player_id=p_home.id, outs=21, er=3, r=3),
        PitchingLine(game_id=g2.id, player_id=p_home.id, outs=21, er=3, r=3),
        PitchingLine(game_id=g1.id, player_id=p_away.id, outs=21, er=1, r=1),
    ])
    db_session.flush()
    refresh_leaderboard_views(db_session)
    db_session.flush()

    resp = client.get(
        "/api/v1/leaderboards/pitching?sort=era&order=asc&qualified=false",
        headers=auth_headers(admin),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body[0]["player_id"] == p_away.id
    assert body[0]["era"] == 1.0
    assert body[1]["player_id"] == p_home.id
    assert body[1]["era"] == 3.0


def test_leaderboard_requires_season_id_when_no_current_season(client, db_session) -> None:
    league = make_league(db_session, name="No Current", slug="no-current")
    admin = make_user(db_session, email="admin@no-current.test", role="admin", league_id=league.id)
    Season(league_id=league.id, year=2025, name="2025", is_current=False)

    resp = client.get("/api/v1/leaderboards/batting", headers=auth_headers(admin))
    assert resp.status_code == 422


def test_leaderboard_explicit_season_id_overrides_current(client, db_session) -> None:
    fx = _build_batting_scenario(db_session, "Explicit")
    other_season = Season(league_id=fx["league"].id, year=2020, name="2020 (empty)", is_current=False)
    db_session.add(other_season)
    db_session.flush()

    resp = client.get(
        f"/api/v1/leaderboards/batting?season_id={other_season.id}&sort=hr&qualified=false",
        headers=auth_headers(fx["admin"]),
    )
    assert resp.status_code == 200
    assert resp.json() == []
