from __future__ import annotations

import json
import time
from queue import Empty, Queue

import paho.mqtt.client as mqtt
import pytest

from .api_helpers import create_execution_events


@pytest.mark.real_mqtt
def test_execution_event_start_stop_publish(client, app):
    # NOTE: This integration test requires docker-compose to be up for Mosquitto.
    create_execution_events(client)
    _set_event_custom_attributes(client, "test_id_1")

    messages, mqtt_client = _listen_for_execution_events(app.config)
    _post_start(client, "test_id_1")
    _post_stop(client, "test_id_1")

    payloads = _drain_messages(messages, expected=2)
    mqtt_client.loop_stop()
    mqtt_client.disconnect()
    _assert_action_payload(payloads[0], "test_id_1", "test_name_1", "START")
    _assert_action_payload(payloads[1], "test_id_1", "test_name_1", "STOP")


def _post_start(client, entity_id: str) -> None:
    resp = client.post(f"/api/execution-events/{entity_id}/start")
    assert resp.status_code == 200


def _post_stop(client, entity_id: str) -> None:
    resp = client.post(f"/api/execution-events/{entity_id}/stop")
    assert resp.status_code == 200


def _set_event_custom_attributes(client, entity_id: str) -> None:
    resp = client.put(
        "/api/execution-events",
        json={
            "id": entity_id,
            "name": "test_name_1",
            "duration_ms": 5000,
            "start_event_attributes": {"brightness": "3000", "gpio_pin": "D4"},
            "stop_event_attributes": {"brightness": "0", "gpio_pin": "D4"},
        },
    )
    assert resp.status_code == 200


def _listen_for_execution_events(config) -> tuple[Queue[str], mqtt.Client]:
    messages: Queue[str] = Queue()
    client = mqtt.Client(client_id="test-execution-events")

    def on_connect(_client, _userdata, _flags, _rc):
        _client.subscribe(config["MQTT_TOPIC_EXECUTION_EVENTS"])

    def on_message(_client, _userdata, msg):
        messages.put(msg.payload.decode("utf-8"))

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(config["MQTT_BROKER_HOST"], config["MQTT_BROKER_PORT"], keepalive=30)
    client.loop_start()
    time.sleep(0.1)
    return messages, client


def _drain_messages(messages: Queue[str], expected: int) -> list[str]:
    payloads: list[str] = []
    deadline = time.time() + 2.0
    while len(payloads) < expected and time.time() < deadline:
        try:
            payloads.append(messages.get(timeout=0.2))
        except Empty:
            continue
    assert len(payloads) == expected
    return payloads


def _assert_action_payload(payload: str, entity_id: str, name: str, action: str) -> None:
    data = json.loads(payload)
    assert data["execution_event_id"] == entity_id
    assert data["execution_event_name"] == name
    assert data["action"] == action
    if action == "START":
        assert data["brightness"] == "3000"
    else:
        assert data["brightness"] == "0"
    assert data["gpio_pin"] == "D4"
