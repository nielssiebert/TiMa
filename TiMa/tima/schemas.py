from __future__ import annotations

from .extensions import BaseSchema
from .models import (
    ExecutionEvent,
    ExecutionEventGroup,
    Factor,
    MqttMessage,
    Sequence,
    SequenceItem,
    Trigger,
    User,
)


class ExecutionEventSchema(BaseSchema):
    class Meta(BaseSchema.Meta):
        model = ExecutionEvent


class ExecutionEventGroupSchema(BaseSchema):
    class Meta(BaseSchema.Meta):
        model = ExecutionEventGroup


class TriggerSchema(BaseSchema):
    class Meta(BaseSchema.Meta):
        model = Trigger


class SequenceSchema(BaseSchema):
    class Meta(BaseSchema.Meta):
        model = Sequence


class SequenceItemSchema(BaseSchema):
    class Meta(BaseSchema.Meta):
        model = SequenceItem


class FactorSchema(BaseSchema):
    class Meta(BaseSchema.Meta):
        model = Factor


class UserSchema(BaseSchema):
    class Meta(BaseSchema.Meta):
        model = User
        load_only = ("password_hash",)


class MqttMessageSchema(BaseSchema):
    class Meta(BaseSchema.Meta):
        model = MqttMessage
