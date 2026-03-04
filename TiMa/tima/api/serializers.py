from __future__ import annotations

from typing import Any

from ..models import ExecutionEvent, ExecutionEventGroup, ExecutionEventStatus, Factor, Sequence, SequenceItem, Trigger, User


def serialize_execution_event(entity: ExecutionEvent) -> dict[str, Any]:
    return {
        "id": entity.id,
        "name": entity.name,
        "status": entity.status.value,
        "duration_ms": entity.duration_ms,
        "activated": entity.activated,
        "start_event_attributes": dict(entity.start_event_attributes or {}),
        "stop_event_attributes": dict(entity.stop_event_attributes or {}),
        "execution_event_groups": [g.id for g in entity.execution_event_groups],
        "factors": [f.id for f in entity.factors],
    }


def serialize_execution_event_group(entity: ExecutionEventGroup) -> dict[str, Any]:
    return {
        "id": entity.id,
        "name": entity.name,
        "status": _serialize_execution_event_group_status(entity),
        "execution_events": [e.id for e in entity.execution_events],
    }


def _serialize_execution_event_group_status(entity: ExecutionEventGroup) -> str:
    if not entity.execution_events:
        return ExecutionEventStatus.OFF.value
    all_running = all(event.status == ExecutionEventStatus.ON for event in entity.execution_events)
    return ExecutionEventStatus.ON.value if all_running else ExecutionEventStatus.OFF.value


def serialize_trigger(entity: Trigger) -> dict[str, Any]:
    return {
        "id": entity.id,
        "name": entity.name,
        "date": entity.date.isoformat() if entity.date else None,
        "time": entity.time.isoformat() if entity.time else None,
        "weekdays": entity.weekdays,
        "from_date": entity.from_date.isoformat() if entity.from_date else None,
        "to_date": entity.to_date.isoformat() if entity.to_date else None,
        "activated": entity.activated,
        "recurring": entity.recurring,
        "trigger_type": entity.trigger_type.value,
        "recurrance_type": entity.recurrance_type.value,
        "sequences": [s.id for s in entity.sequences],
    }


def serialize_sequence_item(item: SequenceItem) -> dict[str, Any]:
    sequence_id = item.sequences[0].id if item.sequences else None
    return {
        "id": item.id,
        "sequence_id": sequence_id,
        "order": item.order,
        "execution_event_id": item.execution_event.id if item.execution_event else None,
        "execution_event_group_id": item.execution_event_group.id if item.execution_event_group else None,
    }


def serialize_sequence(entity: Sequence, runtime: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = {
        "id": entity.id,
        "name": entity.name,
        "automatically_created": entity.automatically_created,
        "triggers": [t.id for t in entity.triggers],
        "sequence_items": [serialize_sequence_item(i) for i in entity.sequence_items],
    }
    if runtime is not None:
        payload["runtime"] = runtime
    return payload


def serialize_factor(entity: Factor) -> dict[str, Any]:
    return {
        "id": entity.id,
        "name": entity.name,
        "activated": entity.activated,
        "factor": entity.factor,
        "min_val": entity.min_val,
        "max_val": entity.max_val,
        "execution_events": [e.id for e in entity.execution_events],
    }


def serialize_user(entity: User) -> dict[str, Any]:
    return {
        "id": entity.id,
        "username": entity.username,
        "confirmed": entity.confirmed,
    }
