from app.models import AuditLog, Player, Team
from tests.conftest import auth_headers, make_league, make_user


def _setup(db_session, suffix: str):
    league = make_league(db_session, name=f"Roster {suffix}", slug=f"roster-{suffix.lower()}")
    admin = make_user(
        db_session, email=f"admin@roster-{suffix.lower()}.test", role="admin",
        league_id=league.id,
    )
    power = make_user(
        db_session, email=f"power@roster-{suffix.lower()}.test", role="power",
        league_id=league.id,
    )
    team = Team(league_id=league.id, name=f"{suffix} Team", captain_user_id=power.id)
    db_session.add(team)
    db_session.flush()
    player = Player(league_id=league.id, team_id=team.id, name="Original Name", number=7)
    db_session.add(player)
    db_session.flush()
    return league, admin, power, team, player


def test_power_rename_request_leaves_player_unchanged_until_approved(client, db_session) -> None:
    _, admin, power, team, player = _setup(db_session, "A")

    create_resp = client.post(
        f"/api/v1/teams/{team.id}/roster-requests",
        json={"type": "rename", "payload": {"player_id": player.id, "name": "New Name"}},
        headers=auth_headers(power),
    )
    assert create_resp.status_code == 201
    request_id = create_resp.json()["id"]
    assert create_resp.json()["status"] == "pending"

    db_session.refresh(player)
    assert player.name == "Original Name"

    approve_resp = client.post(
        f"/api/v1/roster-requests/{request_id}/approve", headers=auth_headers(admin),
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "approved"

    db_session.refresh(player)
    assert player.name == "New Name"

    audit = (
        db_session.query(AuditLog)
        .filter(AuditLog.entity == "player", AuditLog.entity_id == player.id)
        .one_or_none()
    )
    assert audit is not None
    assert audit.action == "roster_request_rename"
    assert audit.actor_id == admin.id
    assert audit.before == {"name": "Original Name"}
    assert audit.after == {"name": "New Name"}


def test_admin_rejects_request_with_reason_player_unchanged(client, db_session) -> None:
    _, admin, power, team, player = _setup(db_session, "B")

    create_resp = client.post(
        f"/api/v1/teams/{team.id}/roster-requests",
        json={"type": "rename", "payload": {"player_id": player.id, "name": "Rejected Name"}},
        headers=auth_headers(power),
    )
    request_id = create_resp.json()["id"]

    reject_resp = client.post(
        f"/api/v1/roster-requests/{request_id}/reject",
        json={"reason": "not needed"},
        headers=auth_headers(admin),
    )
    assert reject_resp.status_code == 200
    assert reject_resp.json()["status"] == "rejected"
    assert reject_resp.json()["reason"] == "not needed"

    db_session.refresh(player)
    assert player.name == "Original Name"


def test_power_cannot_approve_requests(client, db_session) -> None:
    _, admin, power, team, player = _setup(db_session, "C")
    create_resp = client.post(
        f"/api/v1/teams/{team.id}/roster-requests",
        json={"type": "rename", "payload": {"player_id": player.id, "name": "X"}},
        headers=auth_headers(power),
    )
    request_id = create_resp.json()["id"]

    resp = client.post(
        f"/api/v1/roster-requests/{request_id}/approve", headers=auth_headers(power),
    )
    assert resp.status_code == 403


def test_power_cannot_request_for_a_team_they_do_not_captain(client, db_session) -> None:
    league, admin, power, team, player = _setup(db_session, "D")
    other_captain = make_user(
        db_session, email="other-captain@roster-d.test", role="power", league_id=league.id,
    )
    other_team = Team(league_id=league.id, name="Other Team", captain_user_id=other_captain.id)
    db_session.add(other_team)
    db_session.flush()

    resp = client.post(
        f"/api/v1/teams/{other_team.id}/roster-requests",
        json={"type": "add", "payload": {"name": "Intruder", "number": 99}},
        headers=auth_headers(power),
    )
    assert resp.status_code == 403


def test_list_roster_requests_scoped_by_role(client, db_session) -> None:
    league, admin, power, team, player = _setup(db_session, "E")
    other_power = make_user(
        db_session, email="other-power@roster-e.test", role="power", league_id=league.id,
    )
    other_team = Team(league_id=league.id, name="Other Team E", captain_user_id=other_power.id)
    db_session.add(other_team)
    db_session.flush()

    client.post(
        f"/api/v1/teams/{team.id}/roster-requests",
        json={"type": "add", "payload": {"name": "P1", "number": 10}},
        headers=auth_headers(power),
    )
    client.post(
        f"/api/v1/teams/{other_team.id}/roster-requests",
        json={"type": "add", "payload": {"name": "P2", "number": 11}},
        headers=auth_headers(other_power),
    )

    admin_view = client.get("/api/v1/roster-requests", headers=auth_headers(admin))
    assert admin_view.status_code == 200
    assert len(admin_view.json()) == 2

    power_view = client.get("/api/v1/roster-requests", headers=auth_headers(power))
    assert power_view.status_code == 200
    assert len(power_view.json()) == 1
    assert power_view.json()[0]["team_id"] == team.id


def test_approve_add_creates_player(client, db_session) -> None:
    _, admin, power, team, _player = _setup(db_session, "F")
    create_resp = client.post(
        f"/api/v1/teams/{team.id}/roster-requests",
        json={"type": "add", "payload": {"name": "Brand New", "number": 42}},
        headers=auth_headers(power),
    )
    request_id = create_resp.json()["id"]

    resp = client.post(
        f"/api/v1/roster-requests/{request_id}/approve", headers=auth_headers(admin),
    )
    assert resp.status_code == 200

    new_player = (
        db_session.query(Player)
        .filter(Player.team_id == team.id, Player.number == 42)
        .one_or_none()
    )
    assert new_player is not None
    assert new_player.name == "Brand New"


def test_approve_remove_soft_deletes_player(client, db_session) -> None:
    _, admin, power, team, player = _setup(db_session, "G")
    create_resp = client.post(
        f"/api/v1/teams/{team.id}/roster-requests",
        json={"type": "remove", "payload": {"player_id": player.id}},
        headers=auth_headers(power),
    )
    request_id = create_resp.json()["id"]

    resp = client.post(
        f"/api/v1/roster-requests/{request_id}/approve", headers=auth_headers(admin),
    )
    assert resp.status_code == 200

    db_session.refresh(player)
    assert player.status == "left"


def test_double_review_is_conflict(client, db_session) -> None:
    _, admin, power, team, player = _setup(db_session, "H")
    create_resp = client.post(
        f"/api/v1/teams/{team.id}/roster-requests",
        json={"type": "rename", "payload": {"player_id": player.id, "name": "Once"}},
        headers=auth_headers(power),
    )
    request_id = create_resp.json()["id"]

    first = client.post(
        f"/api/v1/roster-requests/{request_id}/approve", headers=auth_headers(admin),
    )
    assert first.status_code == 200

    second = client.post(
        f"/api/v1/roster-requests/{request_id}/approve", headers=auth_headers(admin),
    )
    assert second.status_code == 409
