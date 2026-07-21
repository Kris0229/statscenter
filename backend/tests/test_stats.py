from decimal import Decimal

import pytest

from app.services import stats


def test_avg_known_value() -> None:
    assert stats.avg(93, 300) == pytest.approx(0.31)


def test_avg_divide_by_zero_is_none() -> None:
    assert stats.avg(0, 0) is None


def test_obp_known_value_excludes_sh_from_denominator() -> None:
    # denom = ab+bb+hp+sf = 150+20+5+5 = 180; num = h+bb+hp = 50+20+5 = 75
    assert stats.obp(h=50, bb=20, hp=5, ab=150, sf=5) == pytest.approx(75 / 180)


def test_obp_divide_by_zero_is_none() -> None:
    assert stats.obp(h=0, bb=0, hp=0, ab=0, sf=0) is None


def test_slg_known_value() -> None:
    # singles = 50-10-2-5=33; tb = 33 + 2*10 + 3*2 + 4*5 = 33+20+6+20 = 79
    assert stats.slg(h=50, b2=10, b3=2, hr=5, ab=150) == pytest.approx(79 / 150)


def test_slg_divide_by_zero_is_none() -> None:
    assert stats.slg(h=0, b2=0, b3=0, hr=0, ab=0) is None


def test_ops_sums_obp_and_slg() -> None:
    assert stats.ops(0.4, 0.5) == pytest.approx(0.9)


def test_ops_none_if_either_component_is_none() -> None:
    assert stats.ops(None, 0.5) is None
    assert stats.ops(0.4, None) is None


def test_opp_avg_same_formula_as_avg() -> None:
    assert stats.opp_avg(9, 26) == stats.avg(9, 26)


def test_ip_display_matches_spec_example() -> None:
    assert stats.ip_display(22) == "7.1"
    assert stats.ip_display(21) == "7.0"
    assert stats.ip_display(0) == "0.0"


def test_era_uses_season_innings_per_game_not_hardcoded_nine() -> None:
    era_7 = stats.era(er=3, outs=21, innings_per_game=7)
    era_9 = stats.era(er=3, outs=21, innings_per_game=9)
    assert era_7 == pytest.approx(3.0)
    assert era_9 == pytest.approx(9 / 7 * 3)
    assert era_7 != era_9


def test_era_divide_by_zero_is_none() -> None:
    assert stats.era(er=3, outs=0, innings_per_game=7) is None


def test_whip_known_value() -> None:
    # innings = 21/3 = 7; whip = (10+15)/7
    assert stats.whip(bb=10, h=15, outs=21) == pytest.approx(25 / 7)


def test_whip_divide_by_zero_is_none() -> None:
    assert stats.whip(bb=1, h=1, outs=0) is None


def test_batting_qualifier_threshold() -> None:
    factor = Decimal("2.00")
    assert stats.is_batting_qualified(pa=14, team_games=7, factor=factor) is True
    assert stats.is_batting_qualified(pa=13, team_games=7, factor=factor) is False


def test_pitching_qualifier_threshold() -> None:
    factor = Decimal("1.00")
    assert stats.is_pitching_qualified(outs=21, team_games=7, factor=factor) is True
    assert stats.is_pitching_qualified(outs=20, team_games=7, factor=factor) is False


def test_format_rate3_drops_leading_zero() -> None:
    assert stats.format_rate3(0.311) == ".311"
    assert stats.format_rate3(None) == "—"
    assert stats.format_rate3(1.234) == "1.234"


def test_format_rate2_keeps_leading_digit() -> None:
    assert stats.format_rate2(3.857142857) == "3.86"
    assert stats.format_rate2(None) == "—"
