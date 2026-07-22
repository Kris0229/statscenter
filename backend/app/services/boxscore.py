"""Boxscore payload assembly (BUILD_SPEC §6.5, Phase 5)."""
from app.models import BattingLine, Game, PitchingLine, Player, Season, Team
from app.services import stats


def _team_summary(team: Team) -> dict:
    return {"id": team.id, "name": team.name, "logo_url": team.logo_url}


def _running_avg_as_of(db, player_id: int, season_id: int, as_of_game: Game) -> str:
    """Season AVG through and including `as_of_game`, ordered by game_date
    then id so same-date games have a deterministic cutoff."""
    lines = (
        db.query(BattingLine)
        .join(Game, Game.id == BattingLine.game_id)
        .filter(
            BattingLine.player_id == player_id,
            Game.season_id == season_id,
            Game.status == "final",
            (Game.game_date < as_of_game.game_date)
            | ((Game.game_date == as_of_game.game_date) & (Game.id <= as_of_game.id)),
        )
        .all()
    )
    total_h = sum(line.h for line in lines)
    total_ab = sum(line.ab for line in lines)
    return stats.format_rate3(stats.avg(total_h, total_ab))


def _batting(db, game: Game, team_id: int) -> tuple[list[dict], list[BattingLine]]:
    lines = (
        db.query(BattingLine)
        .join(Player, Player.id == BattingLine.player_id)
        .filter(BattingLine.game_id == game.id, Player.team_id == team_id)
        .order_by(BattingLine.bat_order, BattingLine.sub_index)
        .all()
    )
    players = {p.id: p for p in db.query(Player).filter(Player.id.in_({line.player_id for line in lines}))}

    rows = []
    for line in lines:
        player = players[line.player_id]
        rows.append({
            "order": line.bat_order, "sub": line.sub_index, "player_id": player.id,
            "name": player.name, "pos": line.pos,
            "ab": line.ab, "r": line.r, "h": line.h, "rbi": line.rbi,
            "bb": line.bb, "so": line.so,
            "avg": _running_avg_as_of(db, player.id, game.season_id, game),
        })
    return rows, lines


def _batting_notes(rows: list[dict], lines: list[BattingLine]) -> dict:
    notes: dict = {"2B": [], "3B": [], "HR": [], "SB": [], "LOB": None}
    for row, line in zip(rows, lines):
        if line.b2:
            notes["2B"].append(row["name"])
        if line.b3:
            notes["3B"].append(row["name"])
        if line.hr:
            notes["HR"].append(row["name"])
        if line.sb:
            notes["SB"].append(row["name"])
    return notes


def _pitching(db, game: Game, team_id: int, season: Season) -> list[dict]:
    lines = (
        db.query(PitchingLine)
        .join(Player, Player.id == PitchingLine.player_id)
        .filter(PitchingLine.game_id == game.id, Player.team_id == team_id)
        .order_by(PitchingLine.seq)
        .all()
    )
    players = {p.id: p for p in db.query(Player).filter(Player.id.in_({line.player_id for line in lines}))}

    rows = []
    for line in lines:
        player = players[line.player_id]
        rows.append({
            "player_id": player.id, "name": player.name,
            "ip": stats.ip_display(line.outs),
            "h": line.h, "r": line.r, "er": line.er, "bb": line.bb, "so": line.so, "hr": line.hr,
            "era": stats.format_rate2(stats.era(line.er, line.outs, season.innings_per_game)),
            "decision": None if line.decision == "none" else line.decision,
        })
    return rows


def build_boxscore(db, game: Game) -> dict:
    season = db.get(Season, game.season_id)
    home_team = db.get(Team, game.home_team_id)
    away_team = db.get(Team, game.away_team_id)

    home_batting_rows, home_batting_lines = _batting(db, game, home_team.id)
    away_batting_rows, away_batting_lines = _batting(db, game, away_team.id)

    line_score = game.line_score or {}
    home_notes = _batting_notes(home_batting_rows, home_batting_lines)
    away_notes = _batting_notes(away_batting_rows, away_batting_lines)
    home_notes["LOB"] = line_score.get("home_lob")
    away_notes["LOB"] = line_score.get("away_lob")

    return {
        "game": {
            "id": game.id, "date": game.game_date.isoformat(), "venue": game.venue,
            "code": game.code, "status": game.status,
        },
        "line_score": {
            "home": line_score.get("home", []),
            "away": line_score.get("away", []),
            "home_totals": {
                "r": sum(line.r for line in home_batting_lines),
                "h": sum(line.h for line in home_batting_lines),
                "e": line_score.get("home_e", 0),
            },
            "away_totals": {
                "r": sum(line.r for line in away_batting_lines),
                "h": sum(line.h for line in away_batting_lines),
                "e": line_score.get("away_e", 0),
            },
        },
        "home": {
            "team": _team_summary(home_team),
            "batting": home_batting_rows,
            "batting_notes": home_notes,
            "pitching": _pitching(db, game, home_team.id, season),
        },
        "away": {
            "team": _team_summary(away_team),
            "batting": away_batting_rows,
            "batting_notes": away_notes,
            "pitching": _pitching(db, game, away_team.id, season),
        },
    }
