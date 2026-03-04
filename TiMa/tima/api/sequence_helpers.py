from __future__ import annotations

import uuid
from typing import Any

from ..extensions import db
from ..models import (
    ExecutionEvent,
    ExecutionEventGroup,
    Sequence,
    SequenceItem,
    sequence_sequence_item,
    sequence_trigger,
    sequence_item_execution_event,
    sequence_item_execution_event_group,
)


def build_sequence_items(sequence: Sequence, payload: list[dict[str, Any]]) -> list[SequenceItem]:
    items: list[SequenceItem] = []
    for item in payload:
        items.append(_build_sequence_item(item))
    return items


def _build_sequence_item(item: dict[str, Any]) -> SequenceItem:
    item_id, order = _get_item_id_and_order(item)
    execution_event, execution_event_group = _get_item_targets(item)

    item_entity = SequenceItem(id=item_id, order=order)
    item_entity.execution_event = execution_event
    item_entity.execution_event_group = execution_event_group
    return item_entity


def _get_item_id_and_order(item: dict[str, Any]) -> tuple[str, int]:
    item_id = item.get("id") or str(uuid.uuid4())
    order = item.get("order")
    if order is None:
        raise ValueError("sequence_item order is required")
    return item_id, int(order)


def _get_item_targets(item: dict[str, Any]) -> tuple[ExecutionEvent | None, ExecutionEventGroup | None]:
    execution_event_id = item.get("execution_event_id")
    execution_event_group_id = item.get("execution_event_group_id")
    _validate_item_targets(execution_event_id, execution_event_group_id)

    execution_event = _get_execution_event(execution_event_id)
    execution_event_group = _get_execution_event_group(execution_event_group_id)
    return execution_event, execution_event_group


def _validate_item_targets(execution_event_id: str | None, group_id: str | None) -> None:
    if not execution_event_id and not group_id:
        raise ValueError("execution_event_id or execution_event_group_id must be provided")
    if execution_event_id and group_id:
        raise ValueError("Only one of execution_event_id or execution_event_group_id can be provided")


def _get_execution_event(execution_event_id: str | None) -> ExecutionEvent | None:
    if not execution_event_id:
        return None
    execution_event = db.session.get(ExecutionEvent, execution_event_id)
    if execution_event is None:
        raise ValueError("execution_event_id does not exist")
    return execution_event


def _get_execution_event_group(group_id: str | None) -> ExecutionEventGroup | None:
    if not group_id:
        return None
    execution_event_group = db.session.get(ExecutionEventGroup, group_id)
    if execution_event_group is None:
        raise ValueError("execution_event_group_id does not exist")
    return execution_event_group


def create_default_sequence_for_execution_event(entity: ExecutionEvent) -> None:
    sequence_id = f"{entity.id}_default_sequence"
    name = f"{entity.name}_default_sequence"
    if db.session.get(Sequence, sequence_id) is not None:
        return
    sequence = Sequence(id=sequence_id, name=name, automatically_created=True)
    item = SequenceItem(id=f"{entity.id}_default_item", order=1)
    item.execution_event = entity
    sequence.sequence_items = [item]
    db.session.add(sequence)


def rename_default_sequence_for_execution_event(entity: ExecutionEvent) -> None:
    sequence_id = f"{entity.id}_default_sequence"
    sequence = db.session.get(Sequence, sequence_id)
    if sequence and sequence.automatically_created:
        sequence.name = f"{entity.name}_default_sequence"


def create_default_sequence_for_execution_event_group(entity: ExecutionEventGroup) -> None:
    sequence_id = f"{entity.id}_default_sequence"
    name = f"{entity.name}_default_sequence"
    if db.session.get(Sequence, sequence_id) is not None:
        return
    sequence = Sequence(id=sequence_id, name=name, automatically_created=True)
    item = SequenceItem(id=f"{entity.id}_default_item", order=1)
    item.execution_event_group = entity
    sequence.sequence_items = [item]
    db.session.add(sequence)


def rename_default_sequence_for_execution_event_group(entity: ExecutionEventGroup) -> None:
    sequence_id = f"{entity.id}_default_sequence"
    sequence = db.session.get(Sequence, sequence_id)
    if sequence and sequence.automatically_created:
        sequence.name = f"{entity.name}_default_sequence"


def delete_sequence_items_for_execution_event(entity_id: str) -> None:
    items = _find_items_for_execution_event(entity_id)
    _delete_items(items)


def delete_sequence_items_for_execution_event_group(entity_id: str) -> None:
    items = _find_items_for_execution_event_group(entity_id)
    _delete_items(items)


def _find_items_for_execution_event(entity_id: str) -> list[SequenceItem]:
    return (
        SequenceItem.query.join(
            sequence_item_execution_event,
            SequenceItem.id == sequence_item_execution_event.c.sequence_item_id,
        )
        .filter(sequence_item_execution_event.c.execution_event_id == entity_id)
        .all()
    )


def _find_items_for_execution_event_group(entity_id: str) -> list[SequenceItem]:
    return (
        SequenceItem.query.join(
            sequence_item_execution_event_group,
            SequenceItem.id == sequence_item_execution_event_group.c.sequence_item_id,
        )
        .filter(sequence_item_execution_event_group.c.execution_event_group_id == entity_id)
        .all()
    )


def _delete_items(items: list[SequenceItem]) -> None:
    item_ids = [item.id for item in items]
    if not item_ids:
        return
    sequence_ids = _find_automatic_sequence_ids(item_ids)
    _delete_sequence_item_relations(item_ids)
    SequenceItem.query.filter(SequenceItem.id.in_(item_ids)).delete(synchronize_session=False)
    _delete_sequences(sequence_ids)


def _find_automatic_sequence_ids(item_ids: list[str]) -> list[str]:
    return (
        db.session.query(Sequence.id)
        .join(sequence_sequence_item, Sequence.id == sequence_sequence_item.c.sequence_id)
        .filter(sequence_sequence_item.c.sequence_item_id.in_(item_ids))
        .filter(Sequence.automatically_created.is_(True))
        .distinct()
        .all()
    )


def _delete_sequences(sequence_ids: list[tuple[str]]) -> None:
    if not sequence_ids:
        return
    flattened_ids = [sequence_id for (sequence_id,) in sequence_ids]
    _delete_sequence_relations(flattened_ids)
    Sequence.query.filter(Sequence.id.in_(flattened_ids)).delete(synchronize_session=False)


def _delete_sequence_relations(sequence_ids: list[str]) -> None:
    db.session.execute(
        sequence_trigger.delete().where(sequence_trigger.c.sequence_id.in_(sequence_ids))
    )
    db.session.execute(
        sequence_sequence_item.delete().where(
            sequence_sequence_item.c.sequence_id.in_(sequence_ids)
        )
    )


def _delete_sequence_item_relations(item_ids: list[str]) -> None:
    db.session.execute(
        sequence_sequence_item.delete().where(
            sequence_sequence_item.c.sequence_item_id.in_(item_ids)
        )
    )
    db.session.execute(
        sequence_item_execution_event.delete().where(
            sequence_item_execution_event.c.sequence_item_id.in_(item_ids)
        )
    )
    db.session.execute(
        sequence_item_execution_event_group.delete().where(
            sequence_item_execution_event_group.c.sequence_item_id.in_(item_ids)
        )
    )
