from __future__ import annotations

from tima.scheduling import scheduling_service

from .api_helpers import create_execution_events, create_sequences, create_triggers


def test_triggers_gets_and_typeahead(client):
    create_execution_events(client)
    create_sequences(client)
    create_triggers(client)

    resp = client.get("/api/triggers/test_id_2")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["id"] == "test_id_2"
    assert data["name"] == "test_name_2"
    assert data["date"] == "2026-02-28"
    assert data["time"].startswith("21:00:00")
    assert data["recurrance_type"] == "ONE_TIME"
    assert data["recurring"] is True

    resp = client.get("/api/triggers/test_id_3")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["weekdays"] == "MO,TH,SU"
    assert data["recurring"] is True

    resp = client.get("/api/triggers")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 3

    resp = client.get("/api/triggers/find?query=test_name_1")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 1
    assert data[0]["id"] == "test_id_1"


def test_update_trigger_can_stop_related_sequences(client, monkeypatch):
    create_execution_events(client)
    create_sequences(client)
    create_triggers(client)
    stopped_sequence_sets: list[set[str]] = []

    monkeypatch.setattr(
        scheduling_service,
        "stop_sequences",
        lambda sequence_ids: stopped_sequence_sets.append(set(sequence_ids)),
    )

    resp = client.put(
        "/api/triggers",
        json={
            "id": "test_id_2",
            "name": "updated_trigger",
            "sequence_ids": ["test_id_1"],
            "stop_sequences": True,
        },
    )

    assert resp.status_code == 200
    assert stopped_sequence_sets == [{"test_id_1", "test_id_2"}]


def test_trigger_create_rejects_activated(client):
    create_execution_events(client)
    create_sequences(client)

    resp = client.post(
        "/api/triggers",
        json={
            "id": "test_id_4",
            "name": "test_name_4",
            "trigger_type": "START_AT_POINT_IN_TIME",
            "recurrance_type": "TIMER",
            "time": "00:01:00",
            "sequence_ids": ["test_id_1"],
            "activated": False,
        },
    )

    assert resp.status_code == 400
    data = resp.get_json()
    assert data["message"] == "activated must be updated via activate/deactivate endpoints"


def test_trigger_update_rejects_activated(client):
    create_execution_events(client)
    create_sequences(client)
    create_triggers(client)

    resp = client.put(
        "/api/triggers",
        json={"id": "test_id_1", "name": "test_name_1", "activated": False},
    )

    assert resp.status_code == 400
    data = resp.get_json()
    assert data["message"] == "activated must be updated via activate/deactivate endpoints"


def test_trigger_can_be_activated_and_deactivated_via_dedicated_endpoints(client):
    create_execution_events(client)
    create_sequences(client)
    create_triggers(client)

    resp = client.post("/api/triggers/test_id_1/deactivate")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["activated"] is False

    resp = client.post("/api/triggers/test_id_1/activate")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["activated"] is True


def test_timer_update_accepts_empty_weekdays(client):
    create_execution_events(client)
    create_sequences(client)
    create_triggers(client)

    resp = client.put(
        "/api/triggers",
        json={
            "id": "test_id_1",
            "name": "test_name_1",
            "time": "00:00:20",
            "weekdays": [],
        },
    )

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["recurrance_type"] == "TIMER"
    assert data["weekdays"] is None
    assert data["time"].startswith("00:00:20")
