from tests.conftest import auth_headers, make_user
from tests.rtba_sample import build_rtba_game
from tests.test_score_entry import _enter_full_game


def test_report_highlights_match_rtba_fixture(client, db_session) -> None:
    fixture = build_rtba_game(db_session, "Report")
    _enter_full_game(client, fixture)
    game_id = fixture["game"].id
    admin = fixture["admin"]

    resp = client.get(f"/api/v1/games/{game_id}/report-highlights", headers=auth_headers(admin))
    assert resp.status_code == 200
    body = resp.json()

    assert body["away_score"] == 5
    assert body["home_score"] == 3
    assert body["winning_pitcher"] == "李耀明"
    assert body["losing_pitcher"] == "巨人先發"
    assert body["save_pitcher"] is None

    assert {h["player"] for h in body["home_runs"]} == {"巨人4", "運動家3"}
    assert {m["player"] for m in body["multi_hit_batters"]} == {"巨人先發", "李耀明", "運動家3"}
    assert {s["player"] for s in body["big_strikeout_pitchers"]} == {"李耀明"}


def test_power_and_user_cannot_get_highlights_or_create_report(client, db_session) -> None:
    fixture = build_rtba_game(db_session, "HighlightsPerm")
    _enter_full_game(client, fixture)
    game_id = fixture["game"].id
    league = fixture["league"]
    power = make_user(db_session, email="power@hl-perm.test", role="power", league_id=league.id)

    resp = client.get(f"/api/v1/games/{game_id}/report-highlights", headers=auth_headers(power))
    assert resp.status_code == 403

    resp2 = client.post(
        "/api/v1/reports", json={"game_id": game_id}, headers=auth_headers(power),
    )
    assert resp2.status_code == 403


def test_create_report_autofills_title_and_content(client, db_session) -> None:
    fixture = build_rtba_game(db_session, "Autofill")
    _enter_full_game(client, fixture)
    game_id = fixture["game"].id
    admin = fixture["admin"]

    resp = client.post("/api/v1/reports", json={"game_id": game_id}, headers=auth_headers(admin))
    assert resp.status_code == 201
    body = resp.json()
    assert "李耀明" in body["content"]
    assert "巨人" in body["title"]
    assert body["published_at"] is None


def test_create_report_honors_explicit_title_override(client, db_session) -> None:
    fixture = build_rtba_game(db_session, "Override")
    _enter_full_game(client, fixture)
    game_id = fixture["game"].id
    admin = fixture["admin"]

    resp = client.post(
        "/api/v1/reports",
        json={"game_id": game_id, "title": "Custom Title", "content": "Custom body"},
        headers=auth_headers(admin),
    )
    assert resp.status_code == 201
    assert resp.json()["title"] == "Custom Title"
    assert resp.json()["content"] == "Custom body"


def test_power_and_user_cannot_publish_reports(client, db_session) -> None:
    fixture = build_rtba_game(db_session, "Publish")
    _enter_full_game(client, fixture)
    game_id = fixture["game"].id
    admin = fixture["admin"]
    league = fixture["league"]
    power = make_user(db_session, email="power@publish.test", role="power", league_id=league.id)
    user = make_user(db_session, email="user@publish.test", role="user", league_id=league.id)

    create = client.post("/api/v1/reports", json={"game_id": game_id}, headers=auth_headers(admin))
    report_id = create.json()["id"]

    for account in (power, user):
        resp = client.post(f"/api/v1/reports/{report_id}/publish", headers=auth_headers(account))
        assert resp.status_code == 403


def test_draft_report_hidden_until_published(client, db_session) -> None:
    fixture = build_rtba_game(db_session, "Visibility")
    _enter_full_game(client, fixture)
    game_id = fixture["game"].id
    admin = fixture["admin"]
    league = fixture["league"]
    user = make_user(db_session, email="user@visibility.test", role="user", league_id=league.id)

    create = client.post("/api/v1/reports", json={"game_id": game_id}, headers=auth_headers(admin))
    report_id = create.json()["id"]

    draft_view = client.get(f"/api/v1/reports/{report_id}", headers=auth_headers(user))
    assert draft_view.status_code == 404
    admin_draft_view = client.get(f"/api/v1/reports/{report_id}", headers=auth_headers(admin))
    assert admin_draft_view.status_code == 200

    publish = client.post(f"/api/v1/reports/{report_id}/publish", headers=auth_headers(admin))
    assert publish.status_code == 200
    assert publish.json()["published_at"] is not None

    published_view = client.get(f"/api/v1/reports/{report_id}", headers=auth_headers(user))
    assert published_view.status_code == 200


def test_report_cross_tenant_is_404(client, db_session) -> None:
    fixture_a = build_rtba_game(db_session, "TenA")
    fixture_b = build_rtba_game(db_session, "TenB")
    _enter_full_game(client, fixture_b)

    create = client.post(
        "/api/v1/reports", json={"game_id": fixture_b["game"].id},
        headers=auth_headers(fixture_b["admin"]),
    )
    report_id = create.json()["id"]

    resp = client.get(f"/api/v1/reports/{report_id}", headers=auth_headers(fixture_a["admin"]))
    assert resp.status_code == 404
