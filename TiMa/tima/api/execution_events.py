from __future__ import annotations

from typing import Any

from flask import jsonify, request

from ..extensions import db
from ..models import ExecutionEvent, Factor
from ..mqtt_client import mqtt_client
from .common import validation_error
from .serializers import serialize_execution_event
from .sequence_helpers import (
    create_default_sequence_for_execution_event,
    delete_sequence_items_for_execution_event,
    rename_default_sequence_for_execution_event,
)


def get_execution_events():
    entities = ExecutionEvent.query.all()
    return jsonify([serialize_execution_event(e) for e in entities])


def get_execution_event(entity_id: str):
    entity = db.session.get(ExecutionEvent, entity_id)
    if entity is None:
        return validation_error("ExecutionEvent not found", status_code=404)
    return jsonify(serialize_execution_event(entity))


def find_execution_events():
    query = request.args.get("query", "")
    entities = ExecutionEvent.query.filter(ExecutionEvent.name.ilike(f"%{query}%")).all()
    return jsonify([serialize_execution_event(e) for e in entities])


def create_execution_event():
    data = request.get_json(silent=True) or {}
    error = _validate_id_and_name(data)
    if error:
        return error
    error = _validate_unsupported_fields(data)
    if error:
        return error
    if "status" in data:
        return validation_error("status is read-only")
    if _exists(data["id"]):
        return validation_error("id already exists")

    duration_ms, error = _parse_duration_ms(data)
    if error:
        return error
    start_attributes, error = _parse_event_attributes(data.get("start_event_attributes", {}), "start_event_attributes")
    if error:
        return error
    stop_attributes, error = _parse_event_attributes(data.get("stop_event_attributes", {}), "stop_event_attributes")
    if error:
        return error
    factors, error = _load_factors(data)
    if error:
        return error

    event = _build_execution_event(data, duration_ms, start_attributes, stop_attributes, factors)
    db.session.add(event)
    create_default_sequence_for_execution_event(event)
    db.session.commit()
    return jsonify(serialize_execution_event(event)), 201


def update_execution_event():
    data = request.get_json(silent=True) or {}
    error = _validate_id_and_name(data)
    if error:
        return error
    error = _validate_unsupported_fields(data)
    if error:
        return error

    entity = db.session.get(ExecutionEvent, data["id"])
    if entity is None:
        return validation_error("ExecutionEvent not found", status_code=404)
    if "status" in data:
        return validation_error("status is read-only")

    error = _apply_execution_event_updates(entity, data)
    if error:
        return error

    rename_default_sequence_for_execution_event(entity)
    db.session.commit()
    return jsonify(serialize_execution_event(entity))


def delete_execution_event(entity_id: str):
    entity = db.session.get(ExecutionEvent, entity_id)
    if entity is None:
        return validation_error("ExecutionEvent not found", status_code=404)

    entity.execution_event_groups = []
    delete_sequence_items_for_execution_event(entity_id)
    db.session.delete(entity)
    db.session.commit()
    return jsonify({"message": "ok"})


def start_execution_event(entity_id: str):
    entity = db.session.get(ExecutionEvent, entity_id)
    if entity is None:
        return validation_error("ExecutionEvent not found", status_code=404)
    if not entity.activated:
        return validation_error("ExecutionEvent is deactivated")
    mqtt_client.publish_execution_event(entity.id, entity.name, "START")
    return jsonify({"message": "ok"})


def stop_execution_event(entity_id: str):
    entity = db.session.get(ExecutionEvent, entity_id)
    if entity is None:
        return validation_error("ExecutionEvent not found", status_code=404)
    mqtt_client.publish_execution_event(entity.id, entity.name, "STOP")
    return jsonify({"message": "ok"})


def _validate_id_and_name(data: dict[str, Any]):
    if not data.get("id"):
        return validation_error("id is required")
    if not data.get("name"):
        return validation_error("name is required")
    return None


def _validate_unsupported_fields(data: dict[str, Any]):
    if "execution_ms" in data:
        return validation_error("execution_ms is not supported; use duration_ms")
    return None


def _exists(entity_id: str) -> bool:
    return db.session.get(ExecutionEvent, entity_id) is not None


def _parse_duration_ms(data: dict[str, Any]) -> tuple[int | None, Any | None]:
    duration_ms = data.get("duration_ms", 600_000)
    try:
        duration_ms = int(duration_ms)
    except (TypeError, ValueError):
        return None, validation_error("duration_ms must be an integer")
    if duration_ms <= 0:
        return None, validation_error("duration_ms must be positive")
    return duration_ms, None


def _load_factors(data: dict[str, Any]) -> tuple[list[Factor], Any | None]:
    factor_ids = data.get("factor_ids", [])
    if not factor_ids:
        return [], None
    factors = Factor.query.filter(Factor.id.in_(factor_ids)).all()
    if len(factors) != len(factor_ids):
        return [], validation_error("One or more factor_ids do not exist")
    return factors, None


def _build_execution_event(
    data: dict[str, Any],
    duration_ms: int,
    start_attributes: dict[str, str],
    stop_attributes: dict[str, str],
    factors: list[Factor],
) -> ExecutionEvent:
    event = ExecutionEvent(
        id=data["id"],
        name=data["name"],
        duration_ms=duration_ms,
        activated=bool(data.get("activated", True)),
        start_event_attributes=start_attributes,
        stop_event_attributes=stop_attributes,
    )
    event.factors = factors
    return event


def _apply_execution_event_updates(entity: ExecutionEvent, data: dict[str, Any]):
    entity.name = data["name"]
    error = _update_duration(entity, data)
    if error:
        return error
    if "start_event_attributes" in data:
        start_attributes, error = _parse_event_attributes(data["start_event_attributes"], "start_event_attributes")
        if error:
            return error
        entity.start_event_attributes = start_attributes
    if "stop_event_attributes" in data:
        stop_attributes, error = _parse_event_attributes(data["stop_event_attributes"], "stop_event_attributes")
        if error:
            return error
        entity.stop_event_attributes = stop_attributes
    if "activated" in data:
        entity.activated = bool(data["activated"])
    if "factor_ids" in data:
        factors, error = _load_factors(data)
        if error:
            return error
        entity.factors = factors
    return None


def _update_duration(entity: ExecutionEvent, data: dict[str, Any]):
    if "duration_ms" not in data:
        return None
    duration_ms, error = _parse_duration_ms(data)
    if error:
        return error
    entity.duration_ms = duration_ms
    return None


def _parse_event_attributes(raw: Any, field_name: str) -> tuple[dict[str, str], Any | None]:
    if raw is None:
        return {}, None
    if not isinstance(raw, dict):
        return {}, validation_error(f"{field_name} must be an object")

    attributes: dict[str, str] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not key.strip():
            return {}, validation_error(f"{field_name} keys must be non-empty strings")
        if value is None:
            return {}, validation_error(f"{field_name} values cannot be null")
        attributes[key.strip()] = str(value)
    return attributes, None
