"""Finalize-time validation checks (BUILD_SPEC §4.1).

Per-line rules (`pa` breakdown, `h >= b2+b3+hr`, `er <= r`) are already
enforced by DB CHECK constraints at insert time (§3); they're re-verified
here too, defense-in-depth, so /validate can surface them even if a row
somehow got in through another path.

Each check is {name, ok, detail, blocking}. Only `blocking` checks decide
whether /finalize is allowed to proceed — the outs-approximation and RTBA
LOB/PO cross-check are informational only, per §4.1's explicit "warn, not
block" for walk-off/mercy-shortened games.
"""
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import BattingLine, Game, Player, PitchingLine, Season


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str
    blocking: bool = True


def _batting_lines_for_team(db: Session, game_id: int, team_id: int) -> list[BattingLine]:
    return (
        db.query(BattingLine)
        .join(Player, Player.id == BattingLine.player_id)
        .filter(BattingLine.game_id == game_id, Player.team_id == team_id)
        .all()
    )


def _pitching_lines_for_team(db: Session, game_id: int, team_id: int) -> list[PitchingLine]:
    return (
        db.query(PitchingLine)
        .join(Player, Player.id == PitchingLine.player_id)
        .filter(PitchingLine.game_id == game_id, Player.team_id == team_id)
        .all()
    )


def _check_batting_pa_breakdown(lines: list[BattingLine]) -> CheckResult:
    bad = [
        bl.player_id for bl in lines
        if bl.pa != bl.ab + bl.sh + bl.sf + bl.bb + bl.hp + bl.io + bl.tie
    ]
    return CheckResult(
        "batting_pa_breakdown", ok=not bad,
        detail="ok" if not bad else f"pa breakdown mismatch for player_id(s): {bad}",
    )


def _check_batting_hits_consistency(lines: list[BattingLine]) -> CheckResult:
    bad = [bl.player_id for bl in lines if bl.h < bl.b2 + bl.b3 + bl.hr]
    return CheckResult(
        "batting_hits_consistency", ok=not bad,
        detail="ok" if not bad else f"h < 2b+3b+hr for player_id(s): {bad}",
    )


def _check_pitching_er_le_r(lines: list[PitchingLine]) -> CheckResult:
    bad = [pl.player_id for pl in lines if pl.er > pl.r]
    return CheckResult(
        "pitching_er_le_r", ok=not bad,
        detail="ok" if not bad else f"er > r for player_id(s): {bad}",
    )


def _check_runs_match_line_score(
    game: Game, home_batting: list[BattingLine], away_batting: list[BattingLine],
) -> CheckResult:
    line_score = game.line_score or {}
    home_ls = line_score.get("home")
    away_ls = line_score.get("away")
    if home_ls is None or away_ls is None:
        return CheckResult("runs_match_line_score", ok=False, detail="line_score missing home/away innings")

    home_r, away_r = sum(bl.r for bl in home_batting), sum(bl.r for bl in away_batting)
    home_ls_total, away_ls_total = sum(home_ls), sum(away_ls)
    ok = home_r == home_ls_total and away_r == away_ls_total
    detail = (
        "ok" if ok else
        f"home batting r={home_r} vs line_score={home_ls_total}; "
        f"away batting r={away_r} vs line_score={away_ls_total}"
    )
    return CheckResult("runs_match_line_score", ok=ok, detail=detail)


def _check_pitching_runs_cross(
    home_batting: list[BattingLine], away_batting: list[BattingLine],
    home_pitching: list[PitchingLine], away_pitching: list[PitchingLine],
) -> CheckResult:
    home_batting_r = sum(bl.r for bl in home_batting)
    away_batting_r = sum(bl.r for bl in away_batting)
    away_pitching_r = sum(pl.r for pl in away_pitching)  # away pitchers face home batters
    home_pitching_r = sum(pl.r for pl in home_pitching)  # home pitchers face away batters

    ok = away_pitching_r == home_batting_r and home_pitching_r == away_batting_r
    detail = (
        "ok" if ok else
        f"away pitching r={away_pitching_r} vs home batting r={home_batting_r}; "
        f"home pitching r={home_pitching_r} vs away batting r={away_batting_r}"
    )
    return CheckResult("pitching_runs_cross_check", ok=ok, detail=detail)


def _check_outs_approx_game_outs(
    season: Season | None, home_pitching: list[PitchingLine], away_pitching: list[PitchingLine],
) -> CheckResult:
    total_outs = sum(pl.outs for pl in home_pitching) + sum(pl.outs for pl in away_pitching)
    innings = season.innings_per_game if season is not None else 7
    expected = innings * 3 * 2
    ok = total_outs == expected
    detail = (
        "ok" if ok else
        f"total pitching outs={total_outs} vs expected={expected} "
        "(short innings from a walk-off/mercy rule are fine — this is a warning, not a blocker)"
    )
    return CheckResult("outs_approx_game_outs", ok=ok, detail=detail, blocking=False)


def _check_rtba_lob_po_cross(
    game: Game,
    home_batting: list[BattingLine], away_batting: list[BattingLine],
    home_pitching: list[PitchingLine], away_pitching: list[PitchingLine],
) -> CheckResult | None:
    """Σr + LOB + PO == Σpa per team (§4.1). PO derives from the opposing
    pitchers' outs; LOB is an optional manual input carried in `line_score`
    (home_lob/away_lob), mirroring how home_e/away_e already live there.
    Skipped entirely if LOB wasn't provided — there's nothing to check.
    """
    line_score = game.line_score or {}
    home_lob, away_lob = line_score.get("home_lob"), line_score.get("away_lob")
    if home_lob is None or away_lob is None:
        return None

    home_r, away_r = sum(bl.r for bl in home_batting), sum(bl.r for bl in away_batting)
    home_pa, away_pa = sum(bl.pa for bl in home_batting), sum(bl.pa for bl in away_batting)
    home_po = sum(pl.outs for pl in away_pitching)  # outs recorded against home's batters
    away_po = sum(pl.outs for pl in home_pitching)

    home_ok = (home_r + home_lob + home_po) == home_pa
    away_ok = (away_r + away_lob + away_po) == away_pa
    ok = home_ok and away_ok
    detail = (
        "ok" if ok else
        f"home: r({home_r})+lob({home_lob})+po({home_po}) vs pa({home_pa}); "
        f"away: r({away_r})+lob({away_lob})+po({away_po}) vs pa({away_pa})"
    )
    return CheckResult("rtba_lob_po_cross_check", ok=ok, detail=detail, blocking=False)


def run_validation_checks(db: Session, game: Game) -> list[CheckResult]:
    season = db.get(Season, game.season_id)
    home_batting = _batting_lines_for_team(db, game.id, game.home_team_id)
    away_batting = _batting_lines_for_team(db, game.id, game.away_team_id)
    home_pitching = _pitching_lines_for_team(db, game.id, game.home_team_id)
    away_pitching = _pitching_lines_for_team(db, game.id, game.away_team_id)

    checks = [
        _check_batting_pa_breakdown(home_batting + away_batting),
        _check_batting_hits_consistency(home_batting + away_batting),
        _check_pitching_er_le_r(home_pitching + away_pitching),
        _check_runs_match_line_score(game, home_batting, away_batting),
        _check_pitching_runs_cross(home_batting, away_batting, home_pitching, away_pitching),
        _check_outs_approx_game_outs(season, home_pitching, away_pitching),
    ]
    lob_po_check = _check_rtba_lob_po_cross(
        game, home_batting, away_batting, home_pitching, away_pitching,
    )
    if lob_po_check is not None:
        checks.append(lob_po_check)
    return checks


def overall_ok(checks: list[CheckResult]) -> bool:
    return all(c.ok for c in checks if c.blocking)
