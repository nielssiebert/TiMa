from __future__ import annotations

from tima.scheduling import scheduling_service

from .api_helpers import create_execution_events, create_sequences


def test_sequences_gets_and_typeahead(client):
    create_execution_events(client)
    create_sequences(client)

    resp = client.get("/api/sequences/test_id_1")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["id"] == "test_id_1"
    assert data["name"] == "test_name_1"
    assert data["runtime"]["is_running"] is False
    assert data["runtime"]["running_execution_event_ids"] == []
    assert len(data["sequence_items"]) == 2

    items = sorted(data["sequence_items"], key=lambda x: x["order"])
    assert items[0]["order"] == 1
    assert items[0]["execution_event_id"] == "test_id_1"
    assert items[1]["order"] == 2
    assert items[1]["execution_event_id"] == "test_id_2"

    resp = client.get("/api/sequences")
    assert resp.status_code == 200
    data = resp.get_json()
    returned_ids = {item["id"] for item in data}
    assert {"test_id_1", "test_id_2", "test_id_3"}.issubset(returned_ids)
    listed = next(item for item in data if item["id"] == "test_id_1")
    assert listed["runtime"]["is_running"] is False

    resp = client.get("/api/sequences/find?query=test_name_2")
    assert resp.status_code == 200
    data = resp.get_json()
    returned_ids = {item["id"] for item in data}
    assert "test_id_2" in returned_ids
    found = next(item for item in data if item["id"] == "test_id_2")
    assert found["runtime"]["is_running"] is False


def test_sequence_stop_endpoint_calls_scheduling_service(client, monkeypatch):
    create_execution_events(client)
    create_sequences(client)
    stopped_ids: list[str] = []

    monkeypatch.setattr(
        scheduling_service,
        "stop_sequence",
        lambda sequence_id: stopped_ids.append(sequence_id),
    )

    resp = client.post("/api/sequences/test_id_1/stop")

    assert resp.status_code == 200
    assert resp.get_json()["message"] == "ok"
    assert stopped_ids == ["test_id_1"]


def test_sequence_start_endpoint_calls_scheduling_service(client, monkeypatch):
    create_execution_events(client)
    create_sequences(client)
    started_ids: list[str] = []

    monkeypatch.setattr(
        scheduling_service,
        "start_sequence",
        lambda sequence: started_ids.append(sequence.id),
    )

    resp = client.post("/api/sequences/test_id_1/start")

    assert resp.status_code == 200
    assert resp.get_json()["message"] == "ok"
    assert started_ids == ["test_id_1"]


def test_sequence_start_endpoint_returns_not_found_for_unknown_sequence(client):
    resp = client.post("/api/sequences/unknown/start")

    assert resp.status_code == 404
    assert resp.get_json()["error"] == "validationError"
    assert resp.get_json()["message"] == "Sequence not found"


def test_update_automatically_created_sequence_accepts_unchanged_sequence_items(client):
    create_execution_events(client)

    get_resp = client.get("/api/sequences/test_id_1_default_sequence")
    assert get_resp.status_code == 200
    original = get_resp.get_json()

    put_resp = client.put(
        "/api/sequences",
        json={
            "id": "test_id_1_default_sequence",
            "name": "renamed_default_sequence",
            "sequence_items": [
                {
                    "order": item["order"],
                    "execution_event_id": item["execution_event_id"],
                }
                for item in original["sequence_items"]
            ],
        },
    )

    assert put_resp.status_code == 200
    data = put_resp.get_json()
    assert data["name"] == "renamed_default_sequence"


def test_update_automatically_created_sequence_rejects_changed_sequence_items(client):
    create_execution_events(client)

    put_resp = client.put(
        "/api/sequences",
        json={
            "id": "test_id_1_default_sequence",
            "name": "renamed_default_sequence",
            "sequence_items": [
                {
                    "order": 1,
                    "execution_event_id": "test_id_2",
                }
            ],
        },
    )

    assert put_resp.status_code == 400
    data = put_resp.get_json()
    assert data["message"] == "sequence_items cannot be changed for automatically_created sequences"
