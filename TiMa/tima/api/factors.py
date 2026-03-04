from __future__ import annotations

import math
import sys
from typing import Any

from flask import jsonify, request

from ..extensions import db
from ..models import Factor
from ..mqtt_client import mqtt_client
from .common import validation_error
from .serializers import serialize_factor


_MAX_FACTOR_VALUE = sys.float_info.max


def get_factors():
    entities = Factor.query.all()
    return jsonify([serialize_factor(e) for e in entities])


def get_factor(entity_id: str):
    entity = db.session.get(Factor, entity_id)
    if entity is None:
        return validation_error("Factor not found", status_code=404)
    return jsonify(serialize_factor(entity))


def find_factors():
    query = request.args.get("query", "")
    entities = Factor.query.filter(Factor.name.ilike(f"%{query}%")).all()
    return jsonify([serialize_factor(e) for e in entities])


def create_factor():
    data = request.get_json(silent=True) or {}
    error = _validate_id_and_name(data)
    if error:
        return error
    if "factor" in data:
        return validation_error("factor must be updated via updateFactor")
    if "activated" in data:
        return validation_error("activated must be updated via activate/deactivate endpoints")
    if _exists(data["id"]):
        return validation_error("id already exists")

    factor = Factor(
        id=data["id"],
        name=data["name"],
        activated=True,
        min_val=data.get("min_val"),
        max_val=data.get("max_val"),
    )
    db.session.add(factor)
    db.session.commit()

    mqtt_client.publish_factor(factor.id, factor.name)
    return jsonify(serialize_factor(factor)), 201


def update_factor():
    data = request.get_json(silent=True) or {}
    error = _validate_id_and_name(data)
    if error:
        return error

    entity = db.session.get(Factor, data["id"])
    if entity is None:
        return validation_error("Factor not found", status_code=404)

    entity.name = data["name"]
    error = _apply_factor_updates(entity, data)
    if error:
        return error

    db.session.commit()
    mqtt_client.publish_factor(entity.id, entity.name)
    return jsonify(serialize_factor(entity))


def activate_factor(entity_id: str):
    return _set_factor_activation(entity_id, True)


def deactivate_factor(entity_id: str):
    return _set_factor_activation(entity_id, False)


def update_factor_value():
    data = request.get_json(silent=True) or {}
    entity_id = data.get("id")
    value = data.get("value")
    if not entity_id:
        return validation_error("id is required")
    if value is None:
        return validation_error("value is required")

    entity = db.session.get(Factor, entity_id)
    if entity is None:
        return validation_error("Factor not found", status_code=404)

    value, error = _parse_factor_value(value)
    if error:
        return error
    error = _validate_factor_range(entity, value)
    if error:
        return error

    entity.factor = value
    db.session.commit()
    mqtt_client.publish_factor(entity.id, entity.name)
    return jsonify(serialize_factor(entity))


def delete_factor(entity_id: str):
    entity = db.session.get(Factor, entity_id)
    if entity is None:
        return validation_error("Factor not found", status_code=404)
    if entity.execution_events:
        return validation_error("Factor is in use by execution events")
    db.session.delete(entity)
    db.session.commit()
    mqtt_client.publish_factor_deleted(entity_id)
    return jsonify({"message": "ok"})


def _validate_id_and_name(data: dict[str, Any]):
    if not data.get("id"):
        return validation_error("id is required")
    if not data.get("name"):
        return validation_error("name is required")
    return None


def _exists(entity_id: str) -> bool:
    return db.session.get(Factor, entity_id) is not None


def _apply_factor_updates(entity: Factor, data: dict[str, Any]):
    if "factor" in data:
        return validation_error("factor must be updated via updateFactor")
    if "activated" in data:
        return validation_error("activated must be updated via activate/deactivate endpoints")
    if "min_val" in data:
        entity.min_val = data.get("min_val")
    if "max_val" in data:
        entity.max_val = data.get("max_val")
    return None


def _set_factor_activation(entity_id: str, activated: bool):
    entity = db.session.get(Factor, entity_id)
    if entity is None:
        return validation_error("Factor not found", status_code=404)
    entity.activated = activated
    db.session.commit()
    mqtt_client.publish_factor(entity.id, entity.name)
    return jsonify(serialize_factor(entity))


def _parse_factor_value(value: Any):
    try:
        return float(value), None
    except (TypeError, ValueError):
        return None, validation_error("value must be a float")


def _validate_factor_range(entity: Factor, value: float):
    if not math.isfinite(value) or value < 0.0 or value > _MAX_FACTOR_VALUE:
        return validation_error(f"factor must be between 0.0 and {_MAX_FACTOR_VALUE}")
    if entity.min_val is not None and value < entity.min_val:
        return validation_error("factor must be between min_val and max_val")
    if entity.max_val is not None and value > entity.max_val:
        return validation_error("factor must be between min_val and max_val")
    return None
