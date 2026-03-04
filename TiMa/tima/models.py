from __future__ import annotations

from datetime import datetime, date, time
from typing import Optional
from enum import Enum

from sqlalchemy import Boolean, Date, DateTime, Enum as SAEnum, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .extensions import db


class ExecutionEventStatus(str, Enum):
    ON = "ON"
    OFF = "OFF"


class TriggerType(str, Enum):
    START_AT_POINT_IN_TIME = "START_AT_POINT_IN_TIME"
    STOP_AT_POINT_IN_TIME = "STOP_AT_POINT_IN_TIME"


class RecurranceType(str, Enum):
    TIMER = "TIMER"
    ONE_TIME = "ONE_TIME"
    WEEKLY = "WEEKLY"


class ExecutionEventGroup(db.Model):
    __tablename__ = "execution_event_group"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)

    execution_events: Mapped[list[ExecutionEvent]] = relationship(
        "ExecutionEvent",
        secondary="execution_event_group_member",
        back_populates="execution_event_groups",
    )


class ExecutionEvent(db.Model):
    __tablename__ = "execution_event"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[ExecutionEventStatus] = mapped_column(
        SAEnum(ExecutionEventStatus), default=ExecutionEventStatus.OFF, nullable=False
    )
    duration_ms: Mapped[int] = mapped_column(Integer, default=600_000, nullable=False)
    activated: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    start_event_attributes: Mapped[dict[str, str]] = mapped_column(JSON, default=dict, nullable=False)
    stop_event_attributes: Mapped[dict[str, str]] = mapped_column(JSON, default=dict, nullable=False)

    execution_event_groups: Mapped[list[ExecutionEventGroup]] = relationship(
        "ExecutionEventGroup",
        secondary="execution_event_group_member",
        back_populates="execution_events",
    )
    factors: Mapped[list[Factor]] = relationship(
        "Factor",
        secondary="execution_event_factor",
        back_populates="execution_events",
    )


class Trigger(db.Model):
    __tablename__ = "trigger"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    time: Mapped[Optional[time]] = mapped_column(db.Time, nullable=True)
    weekdays: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    from_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    to_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    activated: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    recurring: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    trigger_type: Mapped[TriggerType] = mapped_column(
        SAEnum(TriggerType), nullable=False
    )
    recurrance_type: Mapped[RecurranceType] = mapped_column(
        SAEnum(RecurranceType), nullable=False
    )
    last_scheduled: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    sequences: Mapped[list[Sequence]] = relationship(
        "Sequence",
        secondary="sequence_trigger",
        back_populates="triggers",
    )


class Sequence(db.Model):
    __tablename__ = "sequence"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    automatically_created: Mapped[bool] = mapped_column(Boolean, default=False)

    sequence_items: Mapped[list[SequenceItem]] = relationship(
        "SequenceItem",
        secondary="sequence_sequence_item",
        back_populates="sequences",
    )
    triggers: Mapped[list[Trigger]] = relationship(
        "Trigger",
        secondary="sequence_trigger",
        back_populates="sequences",
    )


class SequenceItem(db.Model):
    __tablename__ = "sequence_item"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    order: Mapped[int] = mapped_column(Integer, nullable=False)

    sequences: Mapped[list[Sequence]] = relationship(
        "Sequence",
        secondary="sequence_sequence_item",
        back_populates="sequence_items",
    )
    execution_event: Mapped[Optional[ExecutionEvent]] = relationship(
        "ExecutionEvent",
        secondary="sequence_item_execution_event",
        uselist=False,
    )
    execution_event_group: Mapped[Optional[ExecutionEventGroup]] = relationship(
        "ExecutionEventGroup",
        secondary="sequence_item_execution_event_group",
        uselist=False,
    )


class Factor(db.Model):
    __tablename__ = "factor"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    activated: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    factor: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    min_val: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_val: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    execution_events: Mapped[list[ExecutionEvent]] = relationship(
        "ExecutionEvent",
        secondary="execution_event_factor",
        back_populates="factors",
    )


class User(db.Model):
    __tablename__ = "user"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class MqttMessage(db.Model):
    __tablename__ = "mqtt_message"

    message_id: Mapped[str] = mapped_column(String, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    entity_id: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(String, nullable=False)
    consumers: Mapped[Optional[str]] = mapped_column(String, nullable=True)


# Association tables
execution_event_group_member = db.Table(
    "execution_event_group_member",
    db.Column("execution_event_group_id", ForeignKey("execution_event_group.id")),
    db.Column("execution_event_id", ForeignKey("execution_event.id")),
)

sequence_trigger = db.Table(
    "sequence_trigger",
    db.Column("sequence_id", ForeignKey("sequence.id")),
    db.Column("trigger_id", ForeignKey("trigger.id")),
)

sequence_sequence_item = db.Table(
    "sequence_sequence_item",
    db.Column("sequence_id", ForeignKey("sequence.id"), primary_key=True),
    db.Column("sequence_item_id", ForeignKey("sequence_item.id"), primary_key=True),
)

sequence_item_execution_event = db.Table(
    "sequence_item_execution_event",
    db.Column("sequence_item_id", ForeignKey("sequence_item.id")),
    db.Column("execution_event_id", ForeignKey("execution_event.id")),
)

sequence_item_execution_event_group = db.Table(
    "sequence_item_execution_event_group",
    db.Column("sequence_item_id", ForeignKey("sequence_item.id")),
    db.Column("execution_event_group_id", ForeignKey("execution_event_group.id")),
)

execution_event_factor = db.Table(
    "execution_event_factor",
    db.Column("execution_event_id", ForeignKey("execution_event.id")),
    db.Column("factor_id", ForeignKey("factor.id")),
)
