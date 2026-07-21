import pytest
from sqlalchemy.exc import IntegrityError

from app.models import BattingLine, Game, League, Player, Season, Team, User


def _make_game_and_player(db_session) -> tuple[Game, Player]:
    league = League(name="Test League", slug="test-league")
    db_session.add(league)
    db_session.flush()

    season = Season(league_id=league.id, year=2026, name="2026")
    home = Team(league_id=league.id, name="Home")
    away = Team(league_id=league.id, name="Away")
    db_session.add_all([season, home, away])
    db_session.flush()

    player = Player(league_id=league.id, team_id=home.id, name="Test Player", number=1)
    db_session.add(player)
    db_session.flush()

    game = Game(
        league_id=league.id, season_id=season.id, game_date="2026-04-01",
        home_team_id=home.id, away_team_id=away.id,
    )
    db_session.add(game)
    db_session.flush()
    return game, player


def test_batting_line_pa_breakdown_check_rejects_mismatch(db_session) -> None:
    game, player = _make_game_and_player(db_session)

    bad_line = BattingLine(
        game_id=game.id, player_id=player.id,
        pa=4, ab=3, sh=0, sf=0, bb=0, hp=0, io=0, tie=0,  # pa != sum(3)
    )
    db_session.add(bad_line)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_batting_line_pa_breakdown_check_accepts_matching(db_session) -> None:
    game, player = _make_game_and_player(db_session)

    good_line = BattingLine(
        game_id=game.id, player_id=player.id,
        pa=4, ab=3, sh=0, sf=0, bb=1, hp=0, io=0, tie=0,
        h=1,
    )
    db_session.add(good_line)
    db_session.flush()  # should not raise


def test_non_super_admin_user_requires_league_id(db_session) -> None:
    user = User(
        league_id=None,
        email="orphan@example.com",
        password_hash="x",
        display_name="Orphan",
        role="admin",
    )
    db_session.add(user)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_super_admin_user_requires_null_league_id(db_session) -> None:
    league = League(name="Some League", slug="some-league")
    db_session.add(league)
    db_session.flush()

    user = User(
        league_id=league.id,
        email="bad-superadmin@example.com",
        password_hash="x",
        display_name="Bad Super Admin",
        role="super_admin",
    )
    db_session.add(user)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()
