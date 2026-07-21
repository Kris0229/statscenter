from app.models import AuditLog
from tests.conftest import auth_headers, make_user
from tests.rtba_sample import build_rtba_game


def _enter_full_game(client, fixture) -> None:
    admin = fixture["admin"]
    game_id = fixture["game"].id

    for team_key, payload_key in (
        ("home_team", "home_batting_payload"), ("away_team", "away_batting_payload"),
    ):
        resp = client.put(
            f"/api/v1/games/{game_id}/batting",
            json={"team_id": fixture[team_key].id, "lines": fixture[payload_key]},
            headers=auth_headers(admin),
        )
        assert resp.status_code == 200, resp.text

    for team_key, payload_key in (
        ("home_team", "home_pitching_payload"), ("away_team", "away_pitching_payload"),
    ):
        resp = client.put(
            f"/api/v1/games/{game_id}/pitching",
            json={"team_id": fixture[team_key].id, "lines": fixture[payload_key]},
            headers=auth_headers(admin),
        )
        assert resp.status_code == 200, resp.text

    resp = client.patch(
        f"/api/v1/games/{game_id}",
        json={"line_score": fixture["line_score"]},
        headers=auth_headers(admin),
    )
    assert resp.status_code == 200, resp.text


def test_rtba_sample_game_validates_and_finalizes_cleanly(client, db_session) -> None:
    fixture = build_rtba_game(db_session, "Happy")
    _enter_full_game(client, fixture)
    game_id = fixture["game"].id
    admin = fixture["admin"]

    validate_resp = client.post(
        f"/api/v1/games/{game_id}/validate", headers=auth_headers(admin),
    )
    assert validate_resp.status_code == 200
    body = validate_resp.json()
    assert body["ok"] is True
    checks_by_name = {c["name"]: c for c in body["checks"]}
    assert checks_by_name["batting_pa_breakdown"]["ok"] is True
    assert checks_by_name["batting_hits_consistency"]["ok"] is True
    assert checks_by_name["pitching_er_le_r"]["ok"] is True
    assert checks_by_name["runs_match_line_score"]["ok"] is True
    assert checks_by_name["pitching_runs_cross_check"]["ok"] is True
    assert checks_by_name["outs_approx_game_outs"]["ok"] is True

    finalize_resp = client.post(
        f"/api/v1/games/{game_id}/finalize", headers=auth_headers(admin),
    )
    assert finalize_resp.status_code == 200
    finalized = finalize_resp.json()
    assert finalized["status"] == "final"
    assert finalized["finalized_at"] is not None

    audit = (
        db_session.query(AuditLog)
        .filter(AuditLog.entity == "game", AuditLog.entity_id == game_id, AuditLog.action == "finalize")
        .one_or_none()
    )
    assert audit is not None
    assert audit.after == {"status": "final"}

    again = client.post(f"/api/v1/games/{game_id}/finalize", headers=auth_headers(admin))
    assert again.status_code == 409


def test_validate_fails_when_a_batter_run_breaks_line_score_total(client, db_session) -> None:
    fixture = build_rtba_game(db_session, "Broken")
    # bump one home batter's r from 1 to 2 -> home batting r sums to 4, but
    # line_score's home total stays 3
    fixture["home_batting_payload"][0]["r"] = 2
    _enter_full_game(client, fixture)
    game_id = fixture["game"].id
    admin = fixture["admin"]

    validate_resp = client.post(
        f"/api/v1/games/{game_id}/validate", headers=auth_headers(admin),
    )
    assert validate_resp.status_code == 200
    body = validate_resp.json()
    assert body["ok"] is False
    checks_by_name = {c["name"]: c for c in body["checks"]}
    assert checks_by_name["runs_match_line_score"]["ok"] is False

    finalize_resp = client.post(
        f"/api/v1/games/{game_id}/finalize", headers=auth_headers(admin),
    )
    assert finalize_resp.status_code == 409

    get_resp = client.get(f"/api/v1/games/{game_id}", headers=auth_headers(admin))
    assert get_resp.json()["status"] == "scheduled"
    assert get_resp.json()["finalized_at"] is None

    audit_count = (
        db_session.query(AuditLog)
        .filter(AuditLog.entity == "game", AuditLog.entity_id == game_id)
        .count()
    )
    assert audit_count == 0


def test_power_and_user_cannot_enter_score_or_finalize(client, db_session) -> None:
    fixture = build_rtba_game(db_session, "Perm")
    league = fixture["league"]
    power = make_user(db_session, email="power@rtba-perm.test", role="power", league_id=league.id)
    game_id = fixture["game"].id

    put_resp = client.put(
        f"/api/v1/games/{game_id}/batting",
        json={"team_id": fixture["home_team"].id, "lines": fixture["home_batting_payload"]},
        headers=auth_headers(power),
    )
    assert put_resp.status_code == 403

    finalize_resp = client.post(f"/api/v1/games/{game_id}/finalize", headers=auth_headers(power))
    assert finalize_resp.status_code == 403


def test_cross_tenant_game_write_is_404(client, db_session) -> None:
    fixture_a = build_rtba_game(db_session, "CrossA")
    fixture_b = build_rtba_game(db_session, "CrossB")

    resp = client.put(
        f"/api/v1/games/{fixture_b['game'].id}/batting",
        json={"team_id": fixture_b["home_team"].id, "lines": fixture_b["home_batting_payload"]},
        headers=auth_headers(fixture_a["admin"]),
    )
    assert resp.status_code == 404

    resp2 = client.post(
        f"/api/v1/games/{fixture_b['game'].id}/finalize", headers=auth_headers(fixture_a["admin"]),
    )
    assert resp2.status_code == 404


def test_batting_line_for_player_not_on_team_is_rejected(client, db_session) -> None:
    fixture = build_rtba_game(db_session, "Roster")
    bad_payload = list(fixture["home_batting_payload"])
    bad_payload[0] = {**bad_payload[0], "player_id": fixture["away_players"][0].id}

    resp = client.put(
        f"/api/v1/games/{fixture['game'].id}/batting",
        json={"team_id": fixture["home_team"].id, "lines": bad_payload},
        headers=auth_headers(fixture["admin"]),
    )
    assert resp.status_code == 422


def test_patch_game_cannot_set_status_final_directly(client, db_session) -> None:
    fixture = build_rtba_game(db_session, "DirectFinal")
    resp = client.patch(
        f"/api/v1/games/{fixture['game'].id}",
        json={"status": "final"},
        headers=auth_headers(fixture["admin"]),
    )
    assert resp.status_code == 422


def test_post_finalize_edits_are_audited(client, db_session) -> None:
    fixture = build_rtba_game(db_session, "PostFinal")
    _enter_full_game(client, fixture)
    game_id = fixture["game"].id
    admin = fixture["admin"]

    finalize_resp = client.post(f"/api/v1/games/{game_id}/finalize", headers=auth_headers(admin))
    assert finalize_resp.status_code == 200

    patch_resp = client.patch(
        f"/api/v1/games/{game_id}", json={"venue": "Corrected Venue"}, headers=auth_headers(admin),
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["venue"] == "Corrected Venue"

    corrected_batting = list(fixture["home_batting_payload"])
    corrected_batting[0] = {**corrected_batting[0], "rbi": corrected_batting[0]["rbi"] + 1}
    put_resp = client.put(
        f"/api/v1/games/{game_id}/batting",
        json={"team_id": fixture["home_team"].id, "lines": corrected_batting},
        headers=auth_headers(admin),
    )
    assert put_resp.status_code == 200

    audit_actions = {
        row.action
        for row in db_session.query(AuditLog).filter(
            AuditLog.entity == "game", AuditLog.entity_id == game_id,
        )
    }
    assert "post_finalize_edit" in audit_actions
    assert "post_finalize_batting_edit" in audit_actions

    venue_audit = (
        db_session.query(AuditLog)
        .filter(AuditLog.entity == "game", AuditLog.entity_id == game_id, AuditLog.action == "post_finalize_edit")
        .one()
    )
    assert venue_audit.before == {"venue": None}
    assert venue_audit.after == {"venue": "Corrected Venue"}
    assert venue_audit.actor_id == admin.id


def test_pre_finalize_edits_are_not_audited(client, db_session) -> None:
    fixture = build_rtba_game(db_session, "PreFinal")
    _enter_full_game(client, fixture)
    game_id = fixture["game"].id

    audit_count = (
        db_session.query(AuditLog)
        .filter(AuditLog.entity == "game", AuditLog.entity_id == game_id)
        .count()
    )
    assert audit_count == 0


def test_create_game_and_list_filters(client, db_session) -> None:
    fixture = build_rtba_game(db_session, "Create")
    admin = fixture["admin"]

    create_resp = client.post(
        "/api/v1/games",
        json={
            "season_id": fixture["season"].id, "game_date": "2026-05-02",
            "home_team_id": fixture["home_team"].id, "away_team_id": fixture["away_team"].id,
            "code": "G7",
        },
        headers=auth_headers(admin),
    )
    assert create_resp.status_code == 201
    new_game_id = create_resp.json()["id"]

    list_resp = client.get(
        f"/api/v1/games?season_id={fixture['season'].id}", headers=auth_headers(admin),
    )
    ids = {g["id"] for g in list_resp.json()}
    assert {fixture["game"].id, new_game_id} <= ids

    scheduled_resp = client.get("/api/v1/games?status=scheduled", headers=auth_headers(admin))
    assert all(g["status"] == "scheduled" for g in scheduled_resp.json())
