from __future__ import annotations

from tima.extensions import db
from tima.models import ExecutionEvent, Sequence

from .api_helpers import create_execution_events, create_factor, create_sequences


def test_execution_events_gets_and_typeahead(client):
    create_execution_events(client)

    resp = client.get("/api/execution-events/test_id_1")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["id"] == "test_id_1"
    assert data["name"] == "test_name_1"
    assert data["duration_ms"] == 5000

    resp = client.get("/api/execution-events")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 2

    resp = client.get("/api/execution-events/find?query=test_name_1")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 1
    assert data[0]["id"] == "test_id_1"


def test_update_execution_event_with_factor(client):
    create_execution_events(client)
    create_factor(client)

    resp = client.put(
        "/api/execution-events",
        json={
            "id": "test_id_1",
            "name": "test_name_1",
            "duration_ms": 5000,
            "factor_ids": ["test_id_1"],
        },
    )
    assert resp.status_code == 200


def test_create_execution_event_with_custom_event_attributes(client):
    resp = client.post(
        "/api/execution-events",
        json={
            "id": "test_id_20",
            "name": "test_name_20",
            "duration_ms": 5000,
            "start_event_attributes": {"brightness": "3000", "gpio_pin": "D4"},
            "stop_event_attributes": {"brightness": "0", "gpio_pin": "D4"},
        },
    )

    assert resp.status_code == 201
    data = resp.get_json()
    assert data["start_event_attributes"]["brightness"] == "3000"
    assert data["start_event_attributes"]["gpio_pin"] == "D4"
    assert data["stop_event_attributes"]["brightness"] == "0"


def test_update_execution_event_rejects_invalid_custom_event_attributes(client):
    create_execution_events(client)

    resp = client.put(
        "/api/execution-events",
        json={
            "id": "test_id_1",
            "name": "test_name_1",
            "start_event_attributes": ["not", "an", "object"],
        },
    )

    assert resp.status_code == 400
    data = resp.get_json()
    assert data["message"] == "start_event_attributes must be an object"


def test_create_execution_event_rejects_execution_ms(client):
    resp = client.post(
        "/api/execution-events",
        json={
            "id": "test_id_10",
            "name": "test_name_10",
            "execution_ms": 1000,
        },
    )

    assert resp.status_code == 400
    data = resp.get_json()
    assert data["message"] == "execution_ms is not supported; use duration_ms"


def test_update_execution_event_rejects_execution_ms(client):
    create_execution_events(client)

    resp = client.put(
        "/api/execution-events",
        json={
            "id": "test_id_1",
            "name": "test_name_1",
            "execution_ms": 1000,
        },
    )

    assert resp.status_code == 400
    data = resp.get_json()
    assert data["message"] == "execution_ms is not supported; use duration_ms"


def test_execution_event_start_and_stop_update_status(client, app):
    create_execution_events(client)

    start_resp = client.post("/api/execution-events/test_id_1/start")
    assert start_resp.status_code == 200

    with app.app_context():
        entity = db.session.get(ExecutionEvent, "test_id_1")
        assert entity is not None
        assert entity.status.value == "ON"

    stop_resp = client.post("/api/execution-events/test_id_1/stop")
    assert stop_resp.status_code == 200

    with app.app_context():
        entity = db.session.get(ExecutionEvent, "test_id_1")
        assert entity is not None
        assert entity.status.value == "OFF"


def test_delete_execution_event_removes_related_sequence_items(client):
    create_execution_events(client)
    create_sequences(client)

    resp = client.delete("/api/execution-events/test_id_2")

    assert resp.status_code == 200
    assert resp.get_json()["message"] == "ok"


def test_delete_execution_event_removes_auto_sequence(client, app):
    create_execution_events(client)

    resp = client.delete("/api/execution-events/test_id_2")

    assert resp.status_code == 200
    with app.app_context():
        assert db.session.get(Sequence, "test_id_2_default_sequence") is None
