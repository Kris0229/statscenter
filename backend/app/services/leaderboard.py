"""Leaderboard query, qualify, sort, rank, and paginate (BUILD_SPEC §6.4).

Reads from mv_batting_season / mv_pitching_season (refreshed on finalize —
see app/services/materialized_views.py), computes the rate stats those views
don't carry, and does sort/rank/paginate in Python rather than SQL: at the
scale this spec targets ("an internal league tool, not high-scale SaaS",
§0.4) loading a season's worth of rows (DoD: <500ms on ~1k lines) is trivial,
and it keeps every formula in the single authoritative place (app/services
/stats.py) instead of duplicating them as SQL expressions.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.models import Game, Player, Season
from app.models.materialized_views import mv_batting_season, mv_pitching_season
from app.services import stats

BATTING_RAW_COLUMNS = [
    "g", "pa", "ab", "r", "h", "b2", "b3", "hr", "rbi", "bb", "hp", "sf", "sh", "so", "sb", "cs",
]
BATTING_RATE_COLUMNS = ["avg", "obp", "slg", "ops"]
BATTING_SORT_COLUMNS = set(BATTING_RAW_COLUMNS) | set(BATTING_RATE_COLUMNS)

PITCHING_RAW_COLUMNS = [
    "g", "gs", "w", "l", "sv", "cg", "sho", "outs", "np", "bf", "ab", "h", "hr", "bb", "hp",
    "so", "r", "er",
]
PITCHING_RATE_COLUMNS = ["era", "whip", "oppavg"]
PITCHING_SORT_COLUMNS = set(PITCHING_RAW_COLUMNS) | set(PITCHING_RATE_COLUMNS)


def resolve_season(db: Session, league_id: int, season_id: int | None) -> Season:
    if season_id is not None:
        season = db.query(Season).filter(
            Season.id == season_id, Season.league_id == league_id,
        ).one_or_none()
        if season is None:
            raise ApiError(404, "season not found", "not_found")
        return season

    season = db.query(Season).filter(
        Season.league_id == league_id, Season.is_current.is_(True),
    ).one_or_none()
    if season is None:
        raise ApiError(
            422, "no current season set for this league; pass season_id explicitly", "invalid_input",
        )
    return season


def team_games_by_team(db: Session, league_id: int, season_id: int) -> dict[int, int]:
    rows = db.query(Game.home_team_id, Game.away_team_id).filter(
        Game.league_id == league_id, Game.season_id == season_id, Game.status == "final",
    ).all()
    counts: dict[int, int] = {}
    for home_id, away_id in rows:
        counts[home_id] = counts.get(home_id, 0) + 1
        counts[away_id] = counts.get(away_id, 0) + 1
    return counts


def _fetch_rows(db: Session, mv_table, league_id: int, season_id: int, team_id: int | None) -> list[dict]:
    query = (
        select(mv_table, Player.name.label("player_name"))
        .join(Player, Player.id == mv_table.c.player_id)
        .where(mv_table.c.league_id == league_id, mv_table.c.season_id == season_id)
    )
    if team_id is not None:
        query = query.where(mv_table.c.team_id == team_id)
    return [dict(row._mapping) for row in db.execute(query)]


def _rank_sort_paginate(rows: list[dict], sort: str, order: str, limit: int, offset: int) -> list[dict]:
    reverse = order == "desc"
    with_value = [r for r in rows if r.get(sort) is not None]
    without_value = [r for r in rows if r.get(sort) is None]
    with_value.sort(key=lambda r: r[sort], reverse=reverse)
    ordered = with_value + without_value

    ranked = []
    prev_value = object()
    rank = 0
    for i, row in enumerate(ordered, start=1):
        value = row.get(sort)
        if value != prev_value:
            rank = i
        ranked.append({**row, "rank": rank})
        prev_value = value

    return ranked[offset:offset + limit]


def build_batting_leaderboard(
    db: Session, league_id: int, season: Season, team_id: int | None,
    sort: str, order: str, qualified: bool, limit: int, offset: int,
) -> list[dict]:
    if sort not in BATTING_SORT_COLUMNS:
        raise ApiError(422, f"unsupported sort column: {sort}", "invalid_input")

    rows = _fetch_rows(db, mv_batting_season, league_id, season.id, team_id)
    team_games = team_games_by_team(db, league_id, season.id)

    for row in rows:
        row["avg"] = stats.round_rate3(stats.avg(row["h"], row["ab"]))
        row["obp"] = stats.round_rate3(stats.obp(row["h"], row["bb"], row["hp"], row["ab"], row["sf"]))
        row["slg"] = stats.round_rate3(stats.slg(row["h"], row["b2"], row["b3"], row["hr"], row["ab"]))
        row["ops"] = stats.round_rate3(stats.ops(row["obp"], row["slg"]))
        row["qualified"] = stats.is_batting_qualified(
            row["pa"], team_games.get(row["team_id"], 0), season.pa_qualifier_factor,
        )

    if qualified and sort in BATTING_RATE_COLUMNS:
        rows = [r for r in rows if r["qualified"]]

    return _rank_sort_paginate(rows, sort, order, limit, offset)


def build_pitching_leaderboard(
    db: Session, league_id: int, season: Season, team_id: int | None,
    sort: str, order: str, qualified: bool, limit: int, offset: int,
) -> list[dict]:
    if sort not in PITCHING_SORT_COLUMNS:
        raise ApiError(422, f"unsupported sort column: {sort}", "invalid_input")

    rows = _fetch_rows(db, mv_pitching_season, league_id, season.id, team_id)
    team_games = team_games_by_team(db, league_id, season.id)

    for row in rows:
        row["era"] = stats.round_rate2(stats.era(row["er"], row["outs"], season.innings_per_game))
        row["whip"] = stats.round_rate2(stats.whip(row["bb"], row["h"], row["outs"]))
        row["oppavg"] = stats.round_rate3(stats.opp_avg(row["h"], row["ab"]))
        row["qualified"] = stats.is_pitching_qualified(
            row["outs"], team_games.get(row["team_id"], 0), season.ip_qualifier_factor,
        )

    if qualified and sort in PITCHING_RATE_COLUMNS:
        rows = [r for r in rows if r["qualified"]]

    return _rank_sort_paginate(rows, sort, order, limit, offset)
