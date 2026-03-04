from __future__ import annotations

from flask.testing import FlaskClient


def create_execution_events(client: FlaskClient) -> None:
    _post_execution_event(client, "test_id_1", "test_name_1", 5000)
    _post_execution_event(client, "test_id_2", "test_name_2", 11000)


def create_execution_event_group(client: FlaskClient) -> None:
    resp = client.post(
        "/api/execution-event-groups",
        json={
            "id": "test_id_1",
            "name": "test_name_1",
            "execution_event_ids": ["test_id_1", "test_id_2"],
        },
    )
    assert resp.status_code == 201


def create_sequences(client: FlaskClient) -> None:
    _post_sequence(
        client,
        "test_id_1",
        "test_name_1",
        [
            {"order": 1, "execution_event_id": "test_id_1"},
            {"order": 2, "execution_event_id": "test_id_2"},
        ],
    )
    _post_sequence(
        client,
        "test_id_2",
        "test_name_2",
        [
            {"order": 1, "execution_event_id": "test_id_1"},
            {"order": 1, "execution_event_id": "test_id_2"},
        ],
    )
    _post_sequence(
        client,
        "test_id_3",
        "test_name_3",
        [
            {"order": 1, "execution_event_id": "test_id_2"},
            {"order": 2, "execution_event_id": "test_id_1"},
        ],
    )


def create_triggers(client: FlaskClient) -> None:
    _post_trigger(
        client,
        "test_id_1",
        "test_name_1",
        {
            "trigger_type": "START_AT_POINT_IN_TIME",
            "recurrance_type": "TIMER",
            "recurring": True,
            "sequence_ids": ["test_id_1"],
            "time": "00:00:10",
        },
    )
    _post_trigger(
        client,
        "test_id_2",
        "test_name_2",
        {
            "trigger_type": "STOP_AT_POINT_IN_TIME",
            "recurrance_type": "ONE_TIME",
            "recurring": True,
            "sequence_ids": ["test_id_2"],
            "date": "28.02.2026",
            "time": "21:00:00",
        },
    )
    _post_trigger(
        client,
        "test_id_3",
        "test_name_3",
        {
            "trigger_type": "START_AT_POINT_IN_TIME",
            "recurrance_type": "WEEKLY",
            "recurring": True,
            "sequence_ids": ["test_id_3"],
            "time": "21:00:00",
            "weekdays": ["MO", "TH", "SU"],
        },
    )


def create_factor(client: FlaskClient) -> None:
    resp = client.post(
        "/api/factors",
        json={
            "id": "test_id_1",
            "name": "test_name_1",
            "min_val": 0.7,
            "max_val": 1.5,
        },
    )
    assert resp.status_code == 201


def _post_execution_event(
    client: FlaskClient,
    entity_id: str,
    name: str,
    duration_ms: int,
) -> None:
    resp = client.post(
        "/api/execution-events",
        json={"id": entity_id, "name": name, "duration_ms": duration_ms},
    )
    assert resp.status_code == 201


def _post_sequence(
    client: FlaskClient,
    entity_id: str,
    name: str,
    items: list[dict[str, object]],
) -> None:
    resp = client.post(
        "/api/sequences",
        json={
            "id": entity_id,
            "name": name,
            "sequence_items": items,
        },
    )
    assert resp.status_code == 201


def _post_trigger(
    client: FlaskClient,
    entity_id: str,
    name: str,
    payload: dict[str, object],
) -> None:
    resp = client.post(
        "/api/triggers",
        json={"id": entity_id, "name": name, **payload},
    )
    assert resp.status_code == 201
