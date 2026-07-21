"""Player stats: career aggregate, per-season breakdown, and game log (§6.4)."""
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models import BattingLine, Game, PitchingLine, Player, Season
from app.models.materialized_views import mv_batting_season, mv_pitching_season
from app.services import stats


def _resolve_innings_per_game(db: Session, league_id: int) -> int:
    """Career ERA needs a single innings_per_game, but the formula (§4) is
    inherently season-scoped. TODO(confirm): if a league ever changes
    innings_per_game between seasons, a combined "career ERA" isn't
    well-defined by the spec — this uses the league's current season (or its
    most recent season, or 7 as a last resort) as a documented simplification.
    Per-season figures below always use that season's own value, so they're
    exact regardless.
    """
    season = db.query(Season).filter(
        Season.league_id == league_id, Season.is_current.is_(True),
    ).one_or_none()
    if season is None:
        season = (
            db.query(Season).filter(Season.league_id == league_id)
            .order_by(Season.year.desc()).first()
        )
    return season.innings_per_game if season is not None else 7


def _add_batting_rates(row: dict) -> dict:
    row["avg"] = stats.round_rate3(stats.avg(row["h"], row["ab"]))
    row["obp"] = stats.round_rate3(stats.obp(row["h"], row["bb"], row["hp"], row["ab"], row["sf"]))
    row["slg"] = stats.round_rate3(stats.slg(row["h"], row["b2"], row["b3"], row["hr"], row["ab"]))
    row["ops"] = stats.round_rate3(stats.ops(row["obp"], row["slg"]))
    return row


def _add_pitching_rates(row: dict, innings_per_game: int) -> dict:
    row["era"] = stats.round_rate2(stats.era(row["er"], row["outs"], innings_per_game))
    row["whip"] = stats.round_rate2(stats.whip(row["bb"], row["h"], row["outs"]))
    row["oppavg"] = stats.round_rate3(stats.opp_avg(row["h"], row["ab"]))
    return row


def build_career_stats(db: Session, player: Player) -> dict:
    b = (
        db.query(
            func.count(func.distinct(BattingLine.game_id)).label("g"),
            func.coalesce(func.sum(BattingLine.pa), 0).label("pa"),
            func.coalesce(func.sum(BattingLine.ab), 0).label("ab"),
            func.coalesce(func.sum(BattingLine.r), 0).label("r"),
            func.coalesce(func.sum(BattingLine.h), 0).label("h"),
            func.coalesce(func.sum(BattingLine.b2), 0).label("b2"),
            func.coalesce(func.sum(BattingLine.b3), 0).label("b3"),
            func.coalesce(func.sum(BattingLine.hr), 0).label("hr"),
            func.coalesce(func.sum(BattingLine.rbi), 0).label("rbi"),
            func.coalesce(func.sum(BattingLine.bb), 0).label("bb"),
            func.coalesce(func.sum(BattingLine.hp), 0).label("hp"),
            func.coalesce(func.sum(BattingLine.sf), 0).label("sf"),
            func.coalesce(func.sum(BattingLine.sh), 0).label("sh"),
            func.coalesce(func.sum(BattingLine.so), 0).label("so"),
            func.coalesce(func.sum(BattingLine.sb), 0).label("sb"),
            func.coalesce(func.sum(BattingLine.cs), 0).label("cs"),
        )
        .join(Game, Game.id == BattingLine.game_id)
        .filter(BattingLine.player_id == player.id, Game.status == "final")
        .one()
    )
    batting = _add_batting_rates(dict(b._mapping))

    p = (
        db.query(
            func.count(func.distinct(PitchingLine.game_id)).label("g"),
            func.coalesce(func.sum(case((PitchingLine.gs.is_(True), 1), else_=0)), 0).label("gs"),
            func.coalesce(func.sum(case((PitchingLine.decision == "W", 1), else_=0)), 0).label("w"),
            func.coalesce(func.sum(case((PitchingLine.decision == "L", 1), else_=0)), 0).label("l"),
            func.coalesce(func.sum(case((PitchingLine.decision == "SV", 1), else_=0)), 0).label("sv"),
            func.coalesce(func.sum(case((PitchingLine.cg.is_(True), 1), else_=0)), 0).label("cg"),
            func.coalesce(func.sum(case((PitchingLine.sho.is_(True), 1), else_=0)), 0).label("sho"),
            func.coalesce(func.sum(PitchingLine.outs), 0).label("outs"),
            func.coalesce(func.sum(PitchingLine.np), 0).label("np"),
            func.coalesce(func.sum(PitchingLine.bf), 0).label("bf"),
            func.coalesce(func.sum(PitchingLine.ab), 0).label("ab"),
            func.coalesce(func.sum(PitchingLine.h), 0).label("h"),
            func.coalesce(func.sum(PitchingLine.hr), 0).label("hr"),
            func.coalesce(func.sum(PitchingLine.bb), 0).label("bb"),
            func.coalesce(func.sum(PitchingLine.hp), 0).label("hp"),
            func.coalesce(func.sum(PitchingLine.so), 0).label("so"),
            func.coalesce(func.sum(PitchingLine.r), 0).label("r"),
            func.coalesce(func.sum(PitchingLine.er), 0).label("er"),
        )
        .join(Game, Game.id == PitchingLine.game_id)
        .filter(PitchingLine.player_id == player.id, Game.status == "final")
        .one()
    )
    innings_per_game = _resolve_innings_per_game(db, player.league_id)
    pitching = _add_pitching_rates(dict(p._mapping), innings_per_game)

    return {"batting": batting, "pitching": pitching}


def build_per_season_stats(db: Session, player: Player) -> list[dict]:
    b_rows = {
        row["season_id"]: dict(row)
        for row in db.execute(
            select(mv_batting_season).where(mv_batting_season.c.player_id == player.id),
        ).mappings()
    }
    p_rows = {
        row["season_id"]: dict(row)
        for row in db.execute(
            select(mv_pitching_season).where(mv_pitching_season.c.player_id == player.id),
        ).mappings()
    }

    season_ids = set(b_rows) | set(p_rows)
    if not season_ids:
        return []
    seasons = {s.id: s for s in db.query(Season).filter(Season.id.in_(season_ids))}

    result = []
    for season_id in sorted(season_ids, key=lambda sid: seasons[sid].year, reverse=True):
        season = seasons[season_id]
        batting = _add_batting_rates(b_rows[season_id]) if season_id in b_rows else None
        pitching = (
            _add_pitching_rates(p_rows[season_id], season.innings_per_game)
            if season_id in p_rows else None
        )
        result.append({
            "season_id": season.id, "season_name": season.name, "season_year": season.year,
            "batting": batting, "pitching": pitching,
        })
    return result


_BATTING_LINE_FIELDS = [
    "pa", "ab", "sh", "sf", "bb", "hp", "io", "tie", "r", "h", "b2", "b3", "hr", "rbi",
    "so", "sb", "cs", "gidp", "e",
]
_PITCHING_LINE_FIELDS = [
    "seq", "decision", "outs", "np", "bf", "ab", "h", "hr", "bb", "hp", "so", "r", "er",
    "wp", "gs", "cg", "sho", "sv", "svo",
]


def build_gamelog(db: Session, player: Player, season_id: int | None) -> list[dict]:
    batting_by_game = {
        bl.game_id: bl for bl in db.query(BattingLine).filter(BattingLine.player_id == player.id)
    }
    pitching_by_game: dict[int, list[PitchingLine]] = {}
    for pl in db.query(PitchingLine).filter(PitchingLine.player_id == player.id):
        pitching_by_game.setdefault(pl.game_id, []).append(pl)

    relevant_game_ids = set(batting_by_game) | set(pitching_by_game)
    if not relevant_game_ids:
        return []

    games_query = db.query(Game).filter(Game.status == "final", Game.id.in_(relevant_game_ids))
    if season_id is not None:
        games_query = games_query.filter(Game.season_id == season_id)
    games = games_query.order_by(Game.game_date, Game.id).all()

    season_innings = {
        s.id: s.innings_per_game
        for s in db.query(Season).filter(Season.id.in_({g.season_id for g in games}))
    }

    entries = []
    for game in games:
        is_home = game.home_team_id == player.team_id
        opponent_team_id = game.away_team_id if is_home else game.home_team_id

        bl = batting_by_game.get(game.id)
        batting = None
        if bl is not None:
            batting = _add_batting_rates({f: getattr(bl, f) for f in _BATTING_LINE_FIELDS})

        pitching = None
        pls = pitching_by_game.get(game.id)
        if pls:
            innings_per_game = season_innings.get(game.season_id, 7)
            pitching = [
                _add_pitching_rates({f: getattr(pl, f) for f in _PITCHING_LINE_FIELDS}, innings_per_game)
                for pl in pls
            ]

        entries.append({
            "game_id": game.id, "game_date": game.game_date, "code": game.code,
            "season_id": game.season_id, "opponent_team_id": opponent_team_id, "is_home": is_home,
            "batting": batting, "pitching": pitching,
        })
    return entries
