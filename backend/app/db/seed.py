"""Demo seed data for local/dev environments.

Creates 2 isolated leagues, each with 1 league admin, 1 season, 2 teams,
and ~9 players (per BUILD_SPEC Phase 1). Run via `python -m app.db.seed`.
Idempotent: safe to run multiple times, matched by natural keys
(league slug, user email, team name within league, player number within team).

Seed passwords are fixed demo values — never used outside local/dev.
"""
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import League, Player, Season, Team, User

SEED_ADMIN_PASSWORD = "ChangeMe123!"

_PLAYER_TEMPLATES = [
    # (name, number, positions, bats, throws)
    ("王建民", 1, "P", "R", "R"),
    ("陳金鋒", 2, "OF", "L", "L"),
    ("彭政閔", 3, "1B", "R", "R"),
    ("張泰山", 4, "3B", "R", "R"),
    ("林智勝", 5, "SS", "R", "R"),
    ("陳鏞基", 6, "OF", "L", "L"),
    ("高國輝", 7, "OF", "R", "R"),
    ("郭嚴文", 8, "C", "R", "R"),
    ("潘武雄", 9, "2B", "S", "R"),
]

_LEAGUES = [
    {"name": "示範聯盟 A", "slug": "demo-league-a"},
    {"name": "示範聯盟 B", "slug": "demo-league-b"},
]


def _get_or_create_league(db: Session, name: str, slug: str) -> League:
    league = db.query(League).filter(League.slug == slug).one_or_none()
    if league is not None:
        return league
    league = League(name=name, slug=slug)
    db.add(league)
    db.flush()
    return league


def _get_or_create_admin(db: Session, league: League, email: str, display_name: str) -> User:
    user = db.query(User).filter(User.email == email).one_or_none()
    if user is not None:
        return user
    user = User(
        league_id=league.id,
        email=email,
        password_hash=hash_password(SEED_ADMIN_PASSWORD),
        display_name=display_name,
        role="admin",
    )
    db.add(user)
    db.flush()
    return user


def _get_or_create_season(db: Session, league: League, year: int, name: str) -> Season:
    season = (
        db.query(Season)
        .filter(Season.league_id == league.id, Season.year == year)
        .one_or_none()
    )
    if season is not None:
        return season
    season = Season(league_id=league.id, year=year, name=name, is_current=True)
    db.add(season)
    db.flush()
    return season


def _get_or_create_team(db: Session, league: League, name: str) -> Team:
    team = (
        db.query(Team)
        .filter(Team.league_id == league.id, Team.name == name)
        .one_or_none()
    )
    if team is not None:
        return team
    team = Team(league_id=league.id, name=name)
    db.add(team)
    db.flush()
    return team


def _get_or_create_player(
    db: Session, league: League, team: Team, name: str, number: int,
    positions: str, bats: str, throws: str,
) -> Player:
    player = (
        db.query(Player)
        .filter(Player.team_id == team.id, Player.number == number)
        .one_or_none()
    )
    if player is not None:
        return player
    player = Player(
        league_id=league.id, team_id=team.id, name=name, number=number,
        positions=positions, bats=bats, throws=throws,
    )
    db.add(player)
    db.flush()
    return player


def seed() -> None:
    db = SessionLocal()
    try:
        for league_spec in _LEAGUES:
            league = _get_or_create_league(db, league_spec["name"], league_spec["slug"])
            _get_or_create_admin(
                db, league,
                email=f"admin@{league.slug}.demo",
                display_name=f"{league.name} 管理員",
            )
            _get_or_create_season(db, league, year=2026, name="2026 球季")

            team_a = _get_or_create_team(db, league, name=f"{league.name} 老虎隊")
            team_b = _get_or_create_team(db, league, name=f"{league.name} 獅子隊")
            teams = [team_a, team_b]

            for i, (name, number, positions, bats, throws) in enumerate(_PLAYER_TEMPLATES):
                team = teams[i % 2]
                _get_or_create_player(db, league, team, name, number, positions, bats, throws)

            db.commit()
            print(f"seeded league: {league.name} ({league.slug})")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
