from __future__ import annotations

from typing import Any

from flask import jsonify, request

from ..extensions import db
from ..models import ExecutionEvent, ExecutionEventGroup
from ..mqtt_client import mqtt_client
from .common import validation_error
from .serializers import serialize_execution_event_group
from .sequence_helpers import (
    create_default_sequence_for_execution_event_group,
    delete_sequence_items_for_execution_event_group,
    rename_default_sequence_for_execution_event_group,
)


def get_execution_event_groups():
    entities = ExecutionEventGroup.query.all()
    return jsonify([serialize_execution_event_group(e) for e in entities])


def get_execution_event_group(entity_id: str):
    entity = db.session.get(ExecutionEventGroup, entity_id)
    if entity is None:
        return validation_error("ExecutionEventGroup not found", status_code=404)
    return jsonify(serialize_execution_event_group(entity))


def find_execution_event_groups():
    query = request.args.get("query", "")
    entities = ExecutionEventGroup.query.filter(
        ExecutionEventGroup.name.ilike(f"%{query}%")
    ).all()
    return jsonify([serialize_execution_event_group(e) for e in entities])


def create_execution_event_group():
    data = request.get_json(silent=True) or {}
    error = _validate_id_and_name(data)
    if error:
        return error
    if _exists(data["id"]):
        return validation_error("id already exists")

    execution_events, error = _load_execution_events(data)
    if error:
        return error

    group = ExecutionEventGroup(id=data["id"], name=data["name"])
    group.execution_events = execution_events
    db.session.add(group)
    create_default_sequence_for_execution_event_group(group)
    db.session.commit()
    return jsonify(serialize_execution_event_group(group)), 201


def update_execution_event_group():
    data = request.get_json(silent=True) or {}
    error = _validate_id_and_name(data)
    if error:
        return error

    entity = db.session.get(ExecutionEventGroup, data["id"])
    if entity is None:
        return validation_error("ExecutionEventGroup not found", status_code=404)

    entity.name = data["name"]
    error = _apply_execution_event_ids(entity, data)
    if error:
        return error

    rename_default_sequence_for_execution_event_group(entity)
    db.session.commit()
    return jsonify(serialize_execution_event_group(entity))


def delete_execution_event_group(entity_id: str):
    entity = db.session.get(ExecutionEventGroup, entity_id)
    if entity is None:
        return validation_error("ExecutionEventGroup not found", status_code=404)

    entity.execution_events = []
    delete_sequence_items_for_execution_event_group(entity_id)
    db.session.delete(entity)
    db.session.commit()
    return jsonify({"message": "ok"})


def start_execution_event_group(entity_id: str):
    entity = db.session.get(ExecutionEventGroup, entity_id)
    if entity is None:
        return validation_error("ExecutionEventGroup not found", status_code=404)
    _publish_execution_event_group(entity, "START")
    return jsonify({"message": "ok"})


def stop_execution_event_group(entity_id: str):
    entity = db.session.get(ExecutionEventGroup, entity_id)
    if entity is None:
        return validation_error("ExecutionEventGroup not found", status_code=404)
    _publish_execution_event_group(entity, "STOP")
    return jsonify({"message": "ok"})


def _validate_id_and_name(data: dict[str, Any]):
    if not data.get("id"):
        return validation_error("id is required")
    if not data.get("name"):
        return validation_error("name is required")
    return None


def _exists(entity_id: str) -> bool:
    return db.session.get(ExecutionEventGroup, entity_id) is not None


def _load_execution_events(data: dict[str, Any]):
    execution_event_ids = data.get("execution_event_ids", [])
    if not execution_event_ids:
        return [], None
    execution_events = ExecutionEvent.query.filter(
        ExecutionEvent.id.in_(execution_event_ids)
    ).all()
    if len(execution_events) != len(execution_event_ids):
        return [], validation_error("One or more execution_event_ids do not exist")
    return execution_events, None


def _apply_execution_event_ids(entity: ExecutionEventGroup, data: dict[str, Any]):
    if "execution_event_ids" not in data:
        return None
    execution_events, error = _load_execution_events(data)
    if error:
        return error
    entity.execution_events = execution_events
    return None


def _publish_execution_event_group(entity: ExecutionEventGroup, action: str) -> None:
    for event in entity.execution_events:
        mqtt_client.publish_execution_event(event.id, event.name, action)
