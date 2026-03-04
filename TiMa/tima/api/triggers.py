from __future__ import annotations

from datetime import date
from typing import Any

from flask import jsonify, request

from ..extensions import db
from ..models import RecurranceType, Sequence, Trigger, TriggerType
from ..scheduling import scheduling_service
from .common import validation_error
from .parsers import normalize_weekdays, parse_date, parse_time
from .serializers import serialize_trigger


def get_triggers():
    entities = Trigger.query.all()
    return jsonify([serialize_trigger(e) for e in entities])


def get_trigger(entity_id: str):
    entity = db.session.get(Trigger, entity_id)
    if entity is None:
        return validation_error("Trigger not found", status_code=404)
    return jsonify(serialize_trigger(entity))


def find_triggers():
    query = request.args.get("query", "")
    entities = Trigger.query.filter(Trigger.name.ilike(f"%{query}%")).all()
    return jsonify([serialize_trigger(e) for e in entities])


def create_trigger():
    data = request.get_json(silent=True) or {}
    error = _validate_id_and_name(data)
    if error:
        return error
    if "activated" in data:
        return validation_error("activated must be updated via activate/deactivate endpoints")
    if _exists(data["id"]):
        return validation_error("id already exists")

    payload, error = _parse_trigger_payload(data)
    if error:
        return error
    error = _validate_recurrance_requirements(payload)
    if error:
        return error

    sequences, error = _load_sequences(data)
    if error:
        return error

    trigger = _build_trigger(data, payload)
    trigger.sequences = sequences
    db.session.add(trigger)
    db.session.commit()
    return jsonify(serialize_trigger(trigger)), 201


def update_trigger():
    data = request.get_json(silent=True) or {}
    error = _validate_id_and_name(data)
    if error:
        return error

    entity = db.session.get(Trigger, data["id"])
    if entity is None:
        return validation_error("Trigger not found", status_code=404)
    previous_sequence_ids = {sequence.id for sequence in entity.sequences}

    error = _apply_trigger_updates(entity, data)
    if error:
        return error

    error = _validate_recurrance_requirements(_payload_from_entity(entity))
    if error:
        return error

    if bool(data.get("stop_sequences", False)):
        current_sequence_ids = {sequence.id for sequence in entity.sequences}
        scheduling_service.stop_sequences(previous_sequence_ids | current_sequence_ids)

    db.session.commit()
    return jsonify(serialize_trigger(entity))


def activate_trigger(entity_id: str):
    return _set_trigger_activation(entity_id, True)


def deactivate_trigger(entity_id: str):
    return _set_trigger_activation(entity_id, False)


def delete_trigger(entity_id: str):
    entity = db.session.get(Trigger, entity_id)
    if entity is None:
        return validation_error("Trigger not found", status_code=404)
    if entity.sequences:
        return validation_error("Trigger is in use by sequences")
    db.session.delete(entity)
    db.session.commit()
    return jsonify({"message": "ok"})


def _validate_id_and_name(data: dict[str, Any]):
    if not data.get("id"):
        return validation_error("id is required")
    if not data.get("name"):
        return validation_error("name is required")
    return None


def _exists(entity_id: str) -> bool:
    return db.session.get(Trigger, entity_id) is not None


def _parse_trigger_payload(data: dict[str, Any]):
    trigger_type_raw = data.get("trigger_type")
    recurrance_type_raw = data.get("recurrance_type")
    if not trigger_type_raw or not recurrance_type_raw:
        return None, validation_error("trigger_type and recurrance_type are required")

    try:
        payload = {
            "trigger_type": TriggerType(trigger_type_raw),
            "recurrance_type": RecurranceType(recurrance_type_raw),
            "date": parse_date(data.get("date")),
            "time": parse_time(data.get("time")),
            "weekdays": normalize_weekdays(data.get("weekdays")),
            "from_date": parse_date(data.get("from_date")),
            "to_date": parse_date(data.get("to_date")),
        }
    except ValueError as exc:
        return None, validation_error(str(exc))
    return payload, None


def _validate_recurrance_requirements(payload: dict[str, Any]):
    recurrance_type = payload["recurrance_type"]
    if recurrance_type == RecurranceType.ONE_TIME:
        return _validate_one_time(payload)
    if recurrance_type == RecurranceType.WEEKLY:
        return _validate_weekly(payload)
    if recurrance_type == RecurranceType.TIMER:
        return _validate_timer(payload)
    return None


def _validate_one_time(payload: dict[str, Any]):
    if not payload["date"]:
        return validation_error("date is required for ONE_TIME")
    if not payload["time"]:
        return validation_error("time is required for ONE_TIME")
    return None


def _validate_weekly(payload: dict[str, Any]):
    if not payload["weekdays"]:
        return validation_error("weekdays are required for WEEKLY")
    if not payload["time"]:
        return validation_error("time is required for WEEKLY")
    return None


def _validate_timer(payload: dict[str, Any]):
    if not payload["time"]:
        return validation_error("time is required for TIMER")
    if not payload["date"]:
        payload["date"] = date.today()
    return None


def _load_sequences(data: dict[str, Any]):
    sequence_ids = data.get("sequence_ids", [])
    if not sequence_ids:
        return [], None
    sequences = Sequence.query.filter(Sequence.id.in_(sequence_ids)).all()
    if len(sequences) != len(sequence_ids):
        return [], validation_error("One or more sequence_ids do not exist")
    return sequences, None


def _build_trigger(data: dict[str, Any], payload: dict[str, Any]) -> Trigger:
    return Trigger(
        id=data["id"],
        name=data["name"],
        date=payload["date"],
        time=payload["time"],
        weekdays=payload["weekdays"],
        from_date=payload["from_date"],
        to_date=payload["to_date"],
        activated=bool(data.get("activated", True)),
        recurring=bool(data.get("recurring", True)),
        trigger_type=payload["trigger_type"],
        recurrance_type=payload["recurrance_type"],
    )


def _apply_trigger_updates(entity: Trigger, data: dict[str, Any]):
    entity.name = data["name"]
    if "activated" in data:
        return validation_error("activated must be updated via activate/deactivate endpoints")
    if "recurrance_type" in data and data["recurrance_type"] != entity.recurrance_type.value:
        return validation_error("recurrance_type cannot be changed")

    error = _apply_dates(entity, data)
    if error:
        return error

    error = _apply_trigger_type(entity, data)
    if error:
        return error

    if "recurring" in data:
        entity.recurring = bool(data["recurring"])

    if "sequence_ids" in data:
        sequences, error = _load_sequences(data)
        if error:
            return error
        entity.sequences = sequences
    return None


def _apply_dates(entity: Trigger, data: dict[str, Any]):
    try:
        if "date" in data:
            entity.date = parse_date(data.get("date"))
        if "time" in data:
            entity.time = parse_time(data.get("time"))
        if "weekdays" in data:
            entity.weekdays = normalize_weekdays(data.get("weekdays"))
        if "from_date" in data:
            entity.from_date = parse_date(data.get("from_date"))
        if "to_date" in data:
            entity.to_date = parse_date(data.get("to_date"))
    except ValueError as exc:
        return validation_error(str(exc))
    return None


def _apply_trigger_type(entity: Trigger, data: dict[str, Any]):
    if "trigger_type" not in data:
        return None
    try:
        entity.trigger_type = TriggerType(data["trigger_type"])
    except ValueError:
        return validation_error("trigger_type is invalid")
    return None


def _payload_from_entity(entity: Trigger) -> dict[str, Any]:
    return {
        "recurrance_type": entity.recurrance_type,
        "date": entity.date,
        "time": entity.time,
        "weekdays": entity.weekdays,
    }


def _set_trigger_activation(entity_id: str, activated: bool):
    entity = db.session.get(Trigger, entity_id)
    if entity is None:
        return validation_error("Trigger not found", status_code=404)
    entity.activated = activated
    db.session.commit()
    return jsonify(serialize_trigger(entity))
