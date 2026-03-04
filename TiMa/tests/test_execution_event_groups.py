from __future__ import annotations

from tima.extensions import db
from tima.models import ExecutionEvent, Sequence

from .api_helpers import create_execution_event_group, create_execution_events


def test_execution_event_groups_gets_and_typeahead(client):
    create_execution_events(client)
    create_execution_event_group(client)

    resp = client.get("/api/execution-event-groups/test_id_1")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["id"] == "test_id_1"
    assert data["name"] == "test_name_1"
    assert data["status"] == "OFF"
    assert set(data["execution_events"]) == {"test_id_1", "test_id_2"}

    resp = client.get("/api/execution-event-groups")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 1
    assert data[0]["status"] == "OFF"

    resp = client.get("/api/execution-event-groups/find?query=test_name_1")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 1
    assert data[0]["id"] == "test_id_1"


def test_execution_event_group_status_reflects_member_execution_events(client):
    create_execution_events(client)
    create_execution_event_group(client)

    start_resp = client.post("/api/execution-events/test_id_1/start")
    assert start_resp.status_code == 200

    resp = client.get("/api/execution-event-groups/test_id_1")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "OFF"

    start_resp = client.post("/api/execution-events/test_id_2/start")
    assert start_resp.status_code == 200

    resp = client.get("/api/execution-event-groups/test_id_1")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ON"


def test_execution_event_group_start_stop_updates_all_member_statuses(client, app):
    create_execution_events(client)
    create_execution_event_group(client)

    start_resp = client.post("/api/execution-event-groups/test_id_1/start")
    assert start_resp.status_code == 200

    with app.app_context():
        event_1 = db.session.get(ExecutionEvent, "test_id_1")
        event_2 = db.session.get(ExecutionEvent, "test_id_2")
        assert event_1 is not None
        assert event_2 is not None
        assert event_1.status.value == "ON"
        assert event_2.status.value == "ON"

    stop_resp = client.post("/api/execution-event-groups/test_id_1/stop")
    assert stop_resp.status_code == 200

    with app.app_context():
        event_1 = db.session.get(ExecutionEvent, "test_id_1")
        event_2 = db.session.get(ExecutionEvent, "test_id_2")
        assert event_1 is not None
        assert event_2 is not None
        assert event_1.status.value == "OFF"
        assert event_2.status.value == "OFF"


def test_delete_execution_event_group_removes_auto_sequence(client, app):
    create_execution_events(client)
    resp = client.post(
        "/api/execution-event-groups",
        json={
            "id": "group_id_1",
            "name": "group_name_1",
            "execution_event_ids": ["test_id_1", "test_id_2"],
        },
    )
    assert resp.status_code == 201

    resp = client.delete("/api/execution-event-groups/group_id_1")

    assert resp.status_code == 200
    with app.app_context():
        assert db.session.get(Sequence, "group_id_1_default_sequence") is None
