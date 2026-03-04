from __future__ import annotations

from typing import Any

from flask import jsonify, request

from ..extensions import db
from ..models import Sequence, Trigger
from ..scheduling import scheduling_service
from .common import validation_error
from .sequence_helpers import build_sequence_items
from .serializers import serialize_sequence


def get_sequences():
    entities = Sequence.query.all()
    return jsonify([_serialize_with_runtime(e) for e in entities])


def get_sequence(entity_id: str):
    entity = db.session.get(Sequence, entity_id)
    if entity is None:
        return validation_error("Sequence not found", status_code=404)
    runtime = scheduling_service.get_sequence_runtime(entity.id)
    return jsonify(serialize_sequence(entity, runtime=runtime))


def find_sequences():
    query = request.args.get("query", "")
    entities = Sequence.query.filter(Sequence.name.ilike(f"%{query}%")).all()
    return jsonify([_serialize_with_runtime(e) for e in entities])


def create_sequence():
    data = request.get_json(silent=True) or {}
    error = _validate_id_and_name(data)
    if error:
        return error
    if _exists(data["id"]):
        return validation_error("id already exists")

    sequence = Sequence(
        id=data["id"],
        name=data["name"],
        automatically_created=bool(data.get("automatically_created", False)),
    )

    error = _apply_sequence_items(sequence, data)
    if error:
        return error
    error = _apply_trigger_ids(sequence, data)
    if error:
        return error

    db.session.add(sequence)
    db.session.commit()
    return jsonify(serialize_sequence(sequence)), 201


def update_sequence():
    data = request.get_json(silent=True) or {}
    error = _validate_id_and_name(data)
    if error:
        return error

    entity = db.session.get(Sequence, data["id"])
    if entity is None:
        return validation_error("Sequence not found", status_code=404)

    entity.name = data["name"]

    error = _validate_automatic_sequence_update(entity, data)
    if error:
        return error

    error = _apply_sequence_items(entity, data)
    if error:
        return error
    error = _apply_trigger_ids(entity, data)
    if error:
        return error

    db.session.commit()
    return jsonify(serialize_sequence(entity))


def delete_sequence(entity_id: str):
    entity = db.session.get(Sequence, entity_id)
    if entity is None:
        return validation_error("Sequence not found", status_code=404)
    _delete_sequence_items(entity)
    db.session.delete(entity)
    db.session.commit()
    return jsonify({"message": "ok"})


def stop_sequence(entity_id: str):
    entity = db.session.get(Sequence, entity_id)
    if entity is None:
        return validation_error("Sequence not found", status_code=404)
    scheduling_service.stop_sequence(entity.id)
    return jsonify({"message": "ok"})


def start_sequence(entity_id: str):
    entity = db.session.get(Sequence, entity_id)
    if entity is None:
        return validation_error("Sequence not found", status_code=404)
    scheduling_service.start_sequence(entity)
    return jsonify({"message": "ok"})


def _validate_id_and_name(data: dict[str, Any]):
    if not data.get("id"):
        return validation_error("id is required")
    if not data.get("name"):
        return validation_error("name is required")
    return None


def _serialize_with_runtime(entity: Sequence):
    runtime = scheduling_service.get_sequence_runtime(entity.id)
    return serialize_sequence(entity, runtime=runtime)


def _exists(entity_id: str) -> bool:
    return db.session.get(Sequence, entity_id) is not None


def _apply_sequence_items(sequence: Sequence, data: dict[str, Any]):
    if "sequence_items" not in data:
        return None
    try:
        sequence.sequence_items = build_sequence_items(sequence, data.get("sequence_items", []))
    except ValueError as exc:
        return validation_error(str(exc))
    return None


def _apply_trigger_ids(sequence: Sequence, data: dict[str, Any]):
    if "trigger_ids" not in data:
        return None
    trigger_ids = data.get("trigger_ids", [])
    if not trigger_ids:
        sequence.triggers = []
        return None
    triggers = Trigger.query.filter(Trigger.id.in_(trigger_ids)).all()
    if len(triggers) != len(trigger_ids):
        return validation_error("One or more trigger_ids do not exist")
    sequence.triggers = triggers
    return None


def _validate_automatic_sequence_update(entity: Sequence, data: dict[str, Any]):
    if entity.automatically_created and "sequence_items" in data:
        return validation_error("sequence_items cannot be changed for automatically_created sequences")
    return None


def _delete_sequence_items(entity: Sequence) -> None:
    items = list(entity.sequence_items)
    entity.sequence_items = []
    for item in items:
        db.session.delete(item)
