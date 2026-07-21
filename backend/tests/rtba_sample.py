"""RTBA sample game fixture (運動家 vs 巨人, G6) used by score-entry tests.

Self-consistent 9-batter-per-team box: 運動家 (away) wins 5-3 over 巨人
(home). Every batting line's own `pa`/`h` breakdown is DB-CHECK-valid, and
team-level sums are engineered so the finalize-blocking checks in
app/services/game_validation.py pass cleanly: home batting r=3 (matches
line_score), away batting r=5, away pitching r=3 (=home batting r), home
pitching r=5 (=away batting r), and both pitchers go the full 7 innings
(21 outs each, 42 total) so even the outs-approximation warning is clean.
"""
from app.models import Game, Player, Season, Team
from tests.conftest import make_league, make_user

# (number, name, ab, bb, h, b2, b3, hr, r, rbi, so)
_HOME_BATTERS = [
    (1, "巨人1", 4, 0, 2, 1, 0, 0, 1, 1, 1),
    (2, "巨人2", 4, 0, 1, 0, 0, 0, 0, 0, 1),
    (3, "巨人3", 4, 0, 1, 0, 0, 0, 1, 1, 0),
    (4, "巨人4", 3, 1, 1, 0, 0, 1, 1, 2, 1),
    (5, "巨人5", 4, 0, 1, 0, 0, 0, 0, 0, 2),
    (6, "巨人6", 4, 0, 1, 0, 0, 0, 0, 0, 1),
    (7, "巨人7", 4, 0, 1, 0, 0, 0, 0, 0, 2),
    (8, "巨人8", 4, 0, 1, 0, 0, 0, 0, 0, 1),
    (9, "巨人9", 3, 1, 0, 0, 0, 0, 0, 0, 1),
]
_AWAY_BATTERS = [
    (1, "運動家1", 4, 0, 2, 1, 0, 0, 1, 1, 1),
    (2, "運動家2", 4, 0, 1, 0, 0, 0, 1, 0, 0),
    (3, "運動家3", 4, 0, 2, 0, 0, 1, 1, 2, 1),
    (4, "運動家4", 4, 0, 1, 0, 0, 0, 0, 1, 1),
    (5, "運動家5", 3, 1, 1, 0, 0, 0, 1, 0, 0),
    (6, "運動家6", 4, 0, 1, 0, 0, 0, 0, 0, 2),
    (7, "運動家7", 4, 0, 1, 0, 0, 0, 0, 0, 1),
    (8, "運動家8", 4, 0, 1, 0, 0, 0, 1, 1, 1),
    (9, "運動家9", 3, 1, 1, 0, 0, 0, 0, 0, 0),
]

# home batting sums: ab=34 bb=2 h=9 r=3 so=10 hr=1
# away batting sums: ab=34 bb=2 h=11 r=5 so=7 hr=1

HOME_PITCHER = dict(
    name="巨人先發", outs=21, h=11, r=5, er=5, bb=2, so=7, hr=1, ab=34,
    decision="L", cg=True, gs=True, sho=False, sv=False, svo=False, wp=0, hp=0, np=112,
)
AWAY_PITCHER = dict(
    name="李耀明", outs=21, h=9, r=3, er=3, bb=2, so=10, hr=1, ab=34,
    decision="W", cg=True, gs=True, sho=False, sv=False, svo=False, wp=0, hp=0, np=101,
)

LINE_SCORE = {
    "home": [0, 1, 0, 0, 2, 0, 0],
    "away": [1, 0, 2, 0, 0, 2, 0],
    "home_e": 1,
    "away_e": 0,
}


def build_rtba_game(db_session, suffix: str = "RTBA") -> dict:
    league = make_league(db_session, name=f"RTBA {suffix}", slug=f"rtba-{suffix.lower()}")
    admin = make_user(
        db_session, email=f"admin@rtba-{suffix.lower()}.test", role="admin", league_id=league.id,
    )
    season = Season(league_id=league.id, year=2026, name="2026", innings_per_game=7)
    home_team = Team(league_id=league.id, name="巨人")
    away_team = Team(league_id=league.id, name="運動家")
    db_session.add_all([season, home_team, away_team])
    db_session.flush()

    def _make_players(rows: list[tuple], team: Team) -> list[Player]:
        players = []
        for number, name, *_ in rows:
            p = Player(league_id=league.id, team_id=team.id, name=name, number=number)
            db_session.add(p)
            players.append(p)
        db_session.flush()
        return players

    home_players = _make_players(_HOME_BATTERS, home_team)
    away_players = _make_players(_AWAY_BATTERS, away_team)

    game = Game(
        league_id=league.id, season_id=season.id, game_date="2026-05-01",
        home_team_id=home_team.id, away_team_id=away_team.id, code="G6",
    )
    db_session.add(game)
    db_session.flush()

    def _batting_payload(rows: list[tuple], players: list[Player]) -> list[dict]:
        lines = []
        for player, (number, _name, ab, bb, h, b2, b3, hr, r, rbi, so) in zip(players, rows):
            lines.append({
                "player_id": player.id, "bat_order": number, "pos": "OF",
                "pa": ab + bb, "ab": ab, "bb": bb, "h": h, "b2": b2, "b3": b3, "hr": hr,
                "r": r, "rbi": rbi, "so": so,
            })
        return lines

    return {
        "league": league,
        "admin": admin,
        "season": season,
        "home_team": home_team,
        "away_team": away_team,
        "home_players": home_players,
        "away_players": away_players,
        "game": game,
        "home_batting_payload": _batting_payload(_HOME_BATTERS, home_players),
        "away_batting_payload": _batting_payload(_AWAY_BATTERS, away_players),
        "home_pitching_payload": [
            {"player_id": home_players[0].id, **{k: v for k, v in HOME_PITCHER.items() if k != "name"}},
        ],
        "away_pitching_payload": [
            {"player_id": away_players[0].id, **{k: v for k, v in AWAY_PITCHER.items() if k != "name"}},
        ],
        "line_score": LINE_SCORE,
    }
