from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

import paho.mqtt.client as mqtt
from flask import Flask

from .extensions import db
from .models import ExecutionEvent, ExecutionEventStatus, Factor, MqttMessage


class MqttClient:
    def __init__(self) -> None:
        self._client: mqtt.Client | None = None
        self._app: Flask | None = None

    def init_app(self, app) -> None:
        self._app = app
        client = mqtt.Client(client_id=app.config["MQTT_CLIENT_ID"])
        username = app.config.get("MQTT_USERNAME")
        password = app.config.get("MQTT_PASSWORD")
        if username and password:
            client.username_pw_set(username, password)

        client.on_connect = self._on_connect
        client.on_message = self._on_message

        client.connect(
            app.config["MQTT_BROKER_HOST"],
            app.config["MQTT_BROKER_PORT"],
            keepalive=60,
        )
        client.loop_start()
        self._client = client

    @property
    def client(self) -> mqtt.Client:
        if self._client is None:
            raise RuntimeError("MQTT client not initialized")
        return self._client

    @property
    def app(self) -> Flask:
        if self._app is None:
            raise RuntimeError("Flask app not initialized")
        return self._app

    def publish_execution_event(self, entity_id: str, name: str, action: str) -> str:
        message_id = str(uuid.uuid4())
        payload = {
            "message_id": message_id,
            "current_timestamp": datetime.now().astimezone().isoformat(),
            "execution_event_id": entity_id,
            "execution_event_name": name,
            "action": action,
        }
        payload.update(self._resolve_event_attributes(entity_id, action))
        self.client.publish(
            self.app.config["MQTT_TOPIC_EXECUTION_EVENTS"],
            json.dumps(payload),
            qos=1,
        )
        self._apply_execution_event_status(entity_id, action)
        self._persist_message(message_id, entity_id, json.dumps(payload))
        return message_id

    def publish_factor(self, entity_id: str, name: str) -> str:
        message_id = str(uuid.uuid4())
        payload = {
            "message_id": message_id,
            "factor_id": entity_id,
            "factor_name": name,
        }
        self.client.publish(self.app.config["MQTT_TOPIC_FACTORS"], json.dumps(payload))
        self._persist_message(message_id, entity_id, json.dumps(payload))
        return message_id

    def publish_factor_deleted(self, entity_id: str) -> str:
        message_id = str(uuid.uuid4())
        payload = {"message_id": message_id, "factor_id": entity_id}
        self.client.publish(self.app.config["MQTT_TOPIC_FACTORS"], json.dumps(payload))
        self._persist_message(message_id, entity_id, json.dumps(payload))
        return message_id

    def _persist_message(self, message_id: str, entity_id: str, payload: str) -> None:
        db.session.add(
            MqttMessage(
                message_id=message_id,
                timestamp=datetime.now().astimezone(),
                entity_id=entity_id,
                message=payload,
            )
        )
        db.session.commit()

    def _apply_execution_event_status(self, entity_id: str, action: str) -> None:
        event = db.session.get(ExecutionEvent, entity_id)
        if event is None:
            return
        if action == "START":
            event.status = ExecutionEventStatus.ON
            return
        if action == "STOP":
            event.status = ExecutionEventStatus.OFF

    def _resolve_event_attributes(self, entity_id: str, action: str) -> dict[str, Any]:
        event = db.session.get(ExecutionEvent, entity_id)
        if event is None:
            return {}
        if action == "START":
            return dict(event.start_event_attributes or {})
        if action == "STOP":
            return dict(event.stop_event_attributes or {})
        return {}

    def _on_connect(self, client, userdata, flags, rc) -> None:
        client.subscribe(self.app.config["MQTT_TOPIC_EXECUTION_ACKS"])
        client.subscribe(self.app.config["MQTT_TOPIC_FACTORS_VALUES"])

    def _on_message(self, client, userdata, msg) -> None:
        topic = msg.topic
        payload = msg.payload.decode("utf-8")
        if topic == self.app.config["MQTT_TOPIC_EXECUTION_ACKS"]:
            self._handle_ack_message(payload)
        elif topic == self.app.config["MQTT_TOPIC_FACTORS_VALUES"]:
            self._handle_factor_value(payload)

    def _handle_ack_message(self, payload: str) -> None:
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return

        message_id = data.get("message_id")
        consumer = data.get("consumer")
        if not message_id or not consumer:
            return

        message = db.session.get(MqttMessage, message_id)
        if message is None:
            return

        if message.consumers:
            consumers = {c.strip() for c in message.consumers.split(",") if c.strip()}
        else:
            consumers = set()
        consumers.add(consumer)
        message.consumers = ",".join(sorted(consumers))
        db.session.commit()

    def _handle_factor_value(self, payload: str) -> None:
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return
        factor_id = data.get("factor_id") or data.get("id")
        value = data.get("value")
        if factor_id is None or value is None:
            return

        try:
            value = float(value)
        except (TypeError, ValueError):
            return

        factor = db.session.get(Factor, factor_id)
        if factor is None:
            self.app.logger.error("Factor id not found: %s", factor_id)
            return

        if factor.min_val is not None and value < factor.min_val:
            self.app.logger.error(
                "Factor value below min_val: %s (min_val=%s)", value, factor.min_val
            )
            return
        if factor.max_val is not None and value > factor.max_val:
            self.app.logger.error(
                "Factor value above max_val: %s (max_val=%s)", value, factor.max_val
            )
            return

        factor.factor = value
        db.session.commit()


mqtt_client = MqttClient()
