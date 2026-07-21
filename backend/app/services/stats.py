"""Stat computation rules (BUILD_SPEC §4).

Pure functions only — no DB access. Every division guards against a zero
denominator by returning `None` (displayed as "—"); the frontend mirrors
formatting only and never recomputes these values itself.
"""
import math
from decimal import Decimal


def total_bases(h: int, b2: int, b3: int, hr: int) -> int:
    singles = h - b2 - b3 - hr
    return singles + 2 * b2 + 3 * b3 + 4 * hr


def avg(h: int, ab: int) -> float | None:
    if ab <= 0:
        return None
    return h / ab


def obp(h: int, bb: int, hp: int, ab: int, sf: int) -> float | None:
    denom = ab + bb + hp + sf
    if denom <= 0:
        return None
    return (h + bb + hp) / denom


def slg(h: int, b2: int, b3: int, hr: int, ab: int) -> float | None:
    if ab <= 0:
        return None
    return total_bases(h, b2, b3, hr) / ab


def ops(obp_val: float | None, slg_val: float | None) -> float | None:
    if obp_val is None or slg_val is None:
        return None
    return obp_val + slg_val


def opp_avg(h: int, ab: int) -> float | None:
    """Opponent batting average against a pitcher — same formula as AVG,
    just sourced from pitching_lines.h / pitching_lines.ab."""
    return avg(h, ab)


def ip_display(outs: int) -> str:
    return f"{outs // 3}.{outs % 3}"


def era(er: int, outs: int, innings_per_game: int) -> float | None:
    if outs <= 0:
        return None
    return er * innings_per_game * 3 / outs


def whip(bb: int, h: int, outs: int) -> float | None:
    if outs <= 0:
        return None
    return (bb + h) / (outs / 3)


def is_batting_qualified(pa: int, team_games: int, factor: Decimal) -> bool:
    return pa >= math.ceil(team_games * float(factor))


def is_pitching_qualified(outs: int, team_games: int, factor: Decimal) -> bool:
    return outs / 3 >= team_games * float(factor)


def round_rate3(x: float | None) -> float | None:
    return None if x is None else round(x, 3)


def round_rate2(x: float | None) -> float | None:
    return None if x is None else round(x, 2)


def format_rate3(x: float | None) -> str:
    """3 decimals, leading zero dropped: 0.311 -> '.311'. None -> '—'."""
    if x is None:
        return "—"
    s = f"{x:.3f}"
    if s.startswith("0."):
        return s[1:]
    if s.startswith("-0."):
        return "-" + s[2:]
    return s


def format_rate2(x: float | None) -> str:
    """2 decimals (ERA/WHIP), no leading-zero drop. None -> '—'."""
    return "—" if x is None else f"{x:.2f}"
