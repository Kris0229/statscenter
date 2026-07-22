from app.models import Game, Season, Team
from tests.conftest import auth_headers, make_league, make_user


def _setup(db_session, suffix: str):
    league = make_league(db_session, name=f"Media {suffix}", slug=f"media-{suffix.lower()}")
    admin = make_user(
        db_session, email=f"admin@media-{suffix.lower()}.test", role="admin", league_id=league.id,
    )
    season = Season(league_id=league.id, year=2026, name="2026")
    home = Team(league_id=league.id, name="Home")
    away = Team(league_id=league.id, name="Away")
    db_session.add_all([season, home, away])
    db_session.flush()
    game = Game(
        league_id=league.id, season_id=season.id, game_date="2026-05-01",
        home_team_id=home.id, away_team_id=away.id,
    )
    db_session.add(game)
    db_session.flush()
    return league, admin, game


def test_upload_photo_appears_on_game_media_wall(client, db_session) -> None:
    _, admin, game = _setup(db_session, "Wall")
    resp = client.post(
        "/api/v1/media",
        data={"type": "photo", "game_id": str(game.id)},
        files={"file": ("photo.jpg", b"\xff\xd8\xfffakejpegbytes", "image/jpeg")},
        headers=auth_headers(admin),
    )
    assert resp.status_code == 201, resp.text
    media_id = resp.json()["id"]
    assert resp.json()["url"].startswith("/media/")

    wall = client.get(f"/api/v1/media?game_id={game.id}", headers=auth_headers(admin))
    assert wall.status_code == 200
    assert any(m["id"] == media_id for m in wall.json())


def test_upload_video_as_youtube_link(client, db_session) -> None:
    _, admin, game = _setup(db_session, "Video")
    resp = client.post(
        "/api/v1/media",
        data={"type": "video", "game_id": str(game.id), "url": "https://youtube.com/watch?v=abc"},
        headers=auth_headers(admin),
    )
    assert resp.status_code == 201
    assert resp.json()["url"] == "https://youtube.com/watch?v=abc"


def test_upload_rejects_disallowed_mime_type(client, db_session) -> None:
    _, admin, game = _setup(db_session, "Mime")
    resp = client.post(
        "/api/v1/media",
        data={"type": "photo", "game_id": str(game.id)},
        files={"file": ("evil.exe", b"MZfake", "application/octet-stream")},
        headers=auth_headers(admin),
    )
    assert resp.status_code == 422


def test_upload_requires_game_or_player(client, db_session) -> None:
    _, admin, _game = _setup(db_session, "Req")
    resp = client.post(
        "/api/v1/media",
        data={"type": "link", "url": "https://example.com/x"},
        headers=auth_headers(admin),
    )
    assert resp.status_code == 422


def test_power_and_user_can_upload_media(client, db_session) -> None:
    league, _admin, game = _setup(db_session, "Roles")
    power = make_user(db_session, email="power@media-roles.test", role="power", league_id=league.id)
    user = make_user(db_session, email="user@media-roles.test", role="user", league_id=league.id)
    for account in (power, user):
        resp = client.post(
            "/api/v1/media",
            data={"type": "link", "game_id": str(game.id), "url": "https://example.com/a"},
            headers=auth_headers(account),
        )
        assert resp.status_code == 201, account.email


def test_admin_can_hide_media_non_admin_cannot(client, db_session) -> None:
    league, admin, game = _setup(db_session, "Hide")
    user = make_user(db_session, email="user@media-hide.test", role="user", league_id=league.id)
    create = client.post(
        "/api/v1/media", data={"type": "link", "game_id": str(game.id), "url": "https://x.test"},
        headers=auth_headers(admin),
    )
    media_id = create.json()["id"]

    forbidden = client.patch(
        f"/api/v1/media/{media_id}", json={"status": "inactive"}, headers=auth_headers(user),
    )
    assert forbidden.status_code == 403

    hidden = client.patch(
        f"/api/v1/media/{media_id}", json={"status": "inactive"}, headers=auth_headers(admin),
    )
    assert hidden.status_code == 200
    assert hidden.json()["status"] == "inactive"

    user_wall = client.get(f"/api/v1/media?game_id={game.id}", headers=auth_headers(user))
    assert media_id not in [m["id"] for m in user_wall.json()]
    admin_wall = client.get(f"/api/v1/media?game_id={game.id}", headers=auth_headers(admin))
    assert media_id in [m["id"] for m in admin_wall.json()]


def test_uploader_can_delete_own_others_cannot(client, db_session) -> None:
    league, admin, game = _setup(db_session, "Del")
    uploader = make_user(db_session, email="uploader@media-del.test", role="user", league_id=league.id)
    other = make_user(db_session, email="other@media-del.test", role="user", league_id=league.id)

    create = client.post(
        "/api/v1/media", data={"type": "link", "game_id": str(game.id), "url": "https://x.test"},
        headers=auth_headers(uploader),
    )
    media_id = create.json()["id"]

    forbidden = client.delete(f"/api/v1/media/{media_id}", headers=auth_headers(other))
    assert forbidden.status_code == 403

    ok = client.delete(f"/api/v1/media/{media_id}", headers=auth_headers(uploader))
    assert ok.status_code == 204

    # admin can delete anyone's
    create2 = client.post(
        "/api/v1/media", data={"type": "link", "game_id": str(game.id), "url": "https://y.test"},
        headers=auth_headers(uploader),
    )
    media_id2 = create2.json()["id"]
    admin_delete = client.delete(f"/api/v1/media/{media_id2}", headers=auth_headers(admin))
    assert admin_delete.status_code == 204


def test_media_cross_tenant_is_404(client, db_session) -> None:
    _, admin_a, _game_a = _setup(db_session, "TenA")
    _, _admin_b, game_b = _setup(db_session, "TenB")
    resp = client.get(f"/api/v1/media?game_id={game_b.id}", headers=auth_headers(admin_a))
    assert resp.status_code == 404
