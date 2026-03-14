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
    if not entity.automatically_created or "sequence_items" not in data:
        return None
    if _payload_sequence_items_match_current(entity, data.get("sequence_items")):
        data.pop("sequence_items", None)
        return None
    return validation_error("sequence_items cannot be changed for automatically_created sequences")


def _payload_sequence_items_match_current(entity: Sequence, payload_items: Any) -> bool:
    if not isinstance(payload_items, list):
        return False
    expected = sorted(_signature_for_entity_item(item) for item in entity.sequence_items)
    actual = _build_payload_signatures(payload_items)
    return actual is not None and actual == expected


def _build_payload_signatures(payload_items: list[Any]) -> list[tuple[int, str | None, str | None]] | None:
    signatures: list[tuple[int, str | None, str | None]] = []
    for item in payload_items:
        if not isinstance(item, dict):
            return None
        order = _parse_payload_order(item)
        if order is None:
            return None
        signature = _signature_for_payload_item(order, item)
        if signature is None:
            return None
        signatures.append(signature)
    return sorted(signatures)


def _parse_payload_order(item: dict[str, Any]) -> int | None:
    raw_order = item.get("order")
    if raw_order is None:
        return None
    try:
        return int(raw_order)
    except (TypeError, ValueError):
        return None


def _signature_for_payload_item(
    order: int,
    item: dict[str, Any],
) -> tuple[int, str | None, str | None] | None:
    execution_event_id = item.get("execution_event_id")
    execution_event_group_id = item.get("execution_event_group_id")
    has_event_id = isinstance(execution_event_id, str)
    has_group_id = isinstance(execution_event_group_id, str)
    if has_event_id == has_group_id:
        return None
    event_id = execution_event_id if has_event_id else None
    group_id = execution_event_group_id if has_group_id else None
    return (order, event_id, group_id)


def _signature_for_entity_item(item: Any) -> tuple[int, str | None, str | None]:
    execution_event_id = item.execution_event.id if item.execution_event else None
    execution_event_group_id = item.execution_event_group.id if item.execution_event_group else None
    return (item.order, execution_event_id, execution_event_group_id)


def _delete_sequence_items(entity: Sequence) -> None:
    items = list(entity.sequence_items)
    entity.sequence_items = []
    for item in items:
        db.session.delete(item)
