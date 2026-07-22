"""Auto-fill helpers for the admin report editor (§7: "auto-fill score +
W/L pitcher + highlights (HR, multi-hit, 10+ SO)")."""
from app.models import BattingLine, Game, PitchingLine, Player, Team


def _team_batting(db, game_id: int, team_id: int) -> list[BattingLine]:
    return (
        db.query(BattingLine)
        .join(Player, Player.id == BattingLine.player_id)
        .filter(BattingLine.game_id == game_id, Player.team_id == team_id)
        .all()
    )


def _team_pitching(db, game_id: int, team_id: int) -> list[PitchingLine]:
    return (
        db.query(PitchingLine)
        .join(Player, Player.id == PitchingLine.player_id)
        .filter(PitchingLine.game_id == game_id, Player.team_id == team_id)
        .all()
    )


def _player_name(db, player_id: int) -> str:
    player = db.get(Player, player_id)
    return player.name if player is not None else "?"


def build_report_highlights(db, game: Game) -> dict:
    home_team = db.get(Team, game.home_team_id)
    away_team = db.get(Team, game.away_team_id)

    home_batting = _team_batting(db, game.id, game.home_team_id)
    away_batting = _team_batting(db, game.id, game.away_team_id)
    home_pitching = _team_pitching(db, game.id, game.home_team_id)
    away_pitching = _team_pitching(db, game.id, game.away_team_id)
    all_batting = home_batting + away_batting
    all_pitching = home_pitching + away_pitching

    win = next((pl for pl in all_pitching if pl.decision == "W"), None)
    loss = next((pl for pl in all_pitching if pl.decision == "L"), None)
    save = next((pl for pl in all_pitching if pl.decision == "SV"), None)

    return {
        "home_team_name": home_team.name if home_team else "",
        "away_team_name": away_team.name if away_team else "",
        "home_score": sum(bl.r for bl in home_batting),
        "away_score": sum(bl.r for bl in away_batting),
        "winning_pitcher": _player_name(db, win.player_id) if win else None,
        "losing_pitcher": _player_name(db, loss.player_id) if loss else None,
        "save_pitcher": _player_name(db, save.player_id) if save else None,
        "home_runs": [
            {"player": _player_name(db, bl.player_id), "count": bl.hr}
            for bl in all_batting if bl.hr > 0
        ],
        "multi_hit_batters": [
            {"player": _player_name(db, bl.player_id), "hits": bl.h}
            for bl in all_batting if bl.h >= 2
        ],
        "big_strikeout_pitchers": [
            {"player": _player_name(db, pl.player_id), "so": pl.so}
            for pl in all_pitching if pl.so >= 10
        ],
    }


def default_report_title(game: Game, highlights: dict) -> str:
    return (
        f"{highlights['away_team_name']} {highlights['away_score']} - "
        f"{highlights['home_score']} {highlights['home_team_name']} ({game.game_date})"
    )


def render_auto_content(highlights: dict) -> str:
    lines = [
        f"{highlights['away_team_name']} {highlights['away_score']} - "
        f"{highlights['home_score']} {highlights['home_team_name']}",
    ]
    if highlights["winning_pitcher"]:
        lines.append(f"勝投:{highlights['winning_pitcher']}")
    if highlights["losing_pitcher"]:
        lines.append(f"敗投:{highlights['losing_pitcher']}")
    if highlights["save_pitcher"]:
        lines.append(f"救援:{highlights['save_pitcher']}")
    if highlights["home_runs"]:
        hr_list = ", ".join(
            h["player"] + (f" x{h['count']}" if h["count"] > 1 else "")
            for h in highlights["home_runs"]
        )
        lines.append(f"全壘打:{hr_list}")
    if highlights["multi_hit_batters"]:
        mh_list = ", ".join(f"{m['player']}({m['hits']}安)" for m in highlights["multi_hit_batters"])
        lines.append(f"多安打:{mh_list}")
    if highlights["big_strikeout_pitchers"]:
        so_list = ", ".join(
            f"{s['player']}({s['so']}K)" for s in highlights["big_strikeout_pitchers"]
        )
        lines.append(f"單場十振以上:{so_list}")
    return "\n".join(lines)
