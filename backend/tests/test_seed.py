from sqlalchemy.orm import Session

from app.db.seed import _LEAGUES, seed
from app.models import League, Player, Season, Team, User


def _counts(conn) -> dict:
    session = Session(bind=conn, future=True)
    result = {}
    for spec in _LEAGUES:
        league = session.query(League).filter(League.slug == spec["slug"]).one()
        result[spec["slug"]] = {
            "admins": session.query(User)
                .filter(User.league_id == league.id, User.role == "admin").count(),
            "seasons": session.query(Season).filter(Season.league_id == league.id).count(),
            "teams": session.query(Team).filter(Team.league_id == league.id).count(),
            "players": session.query(Player).filter(Player.league_id == league.id).count(),
        }
    session.close()
    return result


def test_seed_creates_two_isolated_leagues(db_engine, migrated_schema) -> None:
    seed()

    with db_engine.connect() as conn:
        counts = _counts(conn)

    assert set(counts.keys()) == {spec["slug"] for spec in _LEAGUES}
    for slug, c in counts.items():
        assert c["admins"] == 1, slug
        assert c["seasons"] == 1, slug
        assert c["teams"] == 2, slug
        assert c["players"] == 9, slug


def test_seed_is_idempotent(db_engine, migrated_schema) -> None:
    seed()
    with db_engine.connect() as conn:
        first = _counts(conn)

    seed()
    with db_engine.connect() as conn:
        second = _counts(conn)

    assert first == second
