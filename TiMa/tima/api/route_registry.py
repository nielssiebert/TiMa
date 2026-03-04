from __future__ import annotations

from flask import Blueprint

from .common import auth_required
from .execution_event_groups import (
    create_execution_event_group,
    delete_execution_event_group,
    find_execution_event_groups,
    get_execution_event_group,
    get_execution_event_groups,
    start_execution_event_group,
    stop_execution_event_group,
    update_execution_event_group,
)
from .execution_events import (
    create_execution_event,
    delete_execution_event,
    find_execution_events,
    get_execution_event,
    get_execution_events,
    start_execution_event,
    stop_execution_event,
    update_execution_event,
)
from .factors import (
    activate_factor,
    create_factor,
    deactivate_factor,
    delete_factor,
    find_factors,
    get_factor,
    get_factors,
    update_factor,
    update_factor_value,
)
from .sequences import (
    create_sequence,
    delete_sequence,
    find_sequences,
    get_sequence,
    get_sequences,
    start_sequence,
    stop_sequence,
    update_sequence,
)
from .triggers import (
    activate_trigger,
    create_trigger,
    deactivate_trigger,
    delete_trigger,
    find_triggers,
    get_trigger,
    get_triggers,
    update_trigger,
)
from .users import change_password, confirm_user, create_user, get_users, login


def register_routes(bp: Blueprint) -> None:
    _register_auth_routes(bp)
    _register_user_routes(bp)
    _register_execution_event_routes(bp)
    _register_execution_event_group_routes(bp)
    _register_trigger_routes(bp)
    _register_sequence_routes(bp)
    _register_factor_routes(bp)


def _register_auth_routes(bp: Blueprint) -> None:
    _add_open(bp, "/login", login, ["POST"])


def _register_user_routes(bp: Blueprint) -> None:
    _add_auth(bp, "/users", get_users, ["GET"])
    _add_open(bp, "/users", create_user, ["POST"])
    _add_auth(bp, "/users/<string:entity_id>/confirm", confirm_user, ["POST"])
    _add_auth(bp, "/users/change_password", change_password, ["POST"])


def _register_execution_event_routes(bp: Blueprint) -> None:
    _add_auth(bp, "/execution-events", get_execution_events, ["GET"])
    _add_auth(bp, "/execution-events/<string:entity_id>", get_execution_event, ["GET"])
    _add_auth(bp, "/execution-events/find", find_execution_events, ["GET"])
    _add_auth(bp, "/execution-events", create_execution_event, ["POST"])
    _add_auth(bp, "/execution-events", update_execution_event, ["PUT"])
    _add_auth(bp, "/execution-events/<string:entity_id>", delete_execution_event, ["DELETE"])
    _add_auth(bp, "/execution-events/<string:entity_id>/start", start_execution_event, ["POST"])
    _add_auth(bp, "/execution-events/<string:entity_id>/stop", stop_execution_event, ["POST"])


def _register_execution_event_group_routes(bp: Blueprint) -> None:
    _add_auth(bp, "/execution-event-groups", get_execution_event_groups, ["GET"])
    _add_auth(
        bp,
        "/execution-event-groups/<string:entity_id>",
        get_execution_event_group,
        ["GET"],
    )
    _add_auth(bp, "/execution-event-groups/find", find_execution_event_groups, ["GET"])
    _add_auth(bp, "/execution-event-groups", create_execution_event_group, ["POST"])
    _add_auth(bp, "/execution-event-groups", update_execution_event_group, ["PUT"])
    _add_auth(
        bp,
        "/execution-event-groups/<string:entity_id>",
        delete_execution_event_group,
        ["DELETE"],
    )
    _add_auth(
        bp,
        "/execution-event-groups/<string:entity_id>/start",
        start_execution_event_group,
        ["POST"],
    )
    _add_auth(
        bp,
        "/execution-event-groups/<string:entity_id>/stop",
        stop_execution_event_group,
        ["POST"],
    )


def _register_trigger_routes(bp: Blueprint) -> None:
    _add_auth(bp, "/triggers", get_triggers, ["GET"])
    _add_auth(bp, "/triggers/<string:entity_id>", get_trigger, ["GET"])
    _add_auth(bp, "/triggers/find", find_triggers, ["GET"])
    _add_auth(bp, "/triggers", create_trigger, ["POST"])
    _add_auth(bp, "/triggers", update_trigger, ["PUT"])
    _add_auth(bp, "/triggers/<string:entity_id>", delete_trigger, ["DELETE"])
    _add_auth(bp, "/triggers/<string:entity_id>/activate", activate_trigger, ["POST"])
    _add_auth(bp, "/triggers/<string:entity_id>/deactivate", deactivate_trigger, ["POST"])


def _register_sequence_routes(bp: Blueprint) -> None:
    _add_auth(bp, "/sequences", get_sequences, ["GET"])
    _add_auth(bp, "/sequences/<string:entity_id>", get_sequence, ["GET"])
    _add_auth(bp, "/sequences/find", find_sequences, ["GET"])
    _add_auth(bp, "/sequences", create_sequence, ["POST"])
    _add_auth(bp, "/sequences", update_sequence, ["PUT"])
    _add_auth(bp, "/sequences/<string:entity_id>", delete_sequence, ["DELETE"])
    _add_auth(bp, "/sequences/<string:entity_id>/start", start_sequence, ["POST"])
    _add_auth(bp, "/sequences/<string:entity_id>/stop", stop_sequence, ["POST"])


def _register_factor_routes(bp: Blueprint) -> None:
    _add_auth(bp, "/factors", get_factors, ["GET"])
    _add_auth(bp, "/factors/<string:entity_id>", get_factor, ["GET"])
    _add_auth(bp, "/factors/find", find_factors, ["GET"])
    _add_auth(bp, "/factors", create_factor, ["POST"])
    _add_auth(bp, "/factors", update_factor, ["PUT"])
    _add_auth(bp, "/factors/<string:entity_id>", delete_factor, ["DELETE"])
    _add_auth(bp, "/factors/updateFactor", update_factor_value, ["POST"])
    _add_auth(bp, "/factors/<string:entity_id>/activate", activate_factor, ["POST"])
    _add_auth(bp, "/factors/<string:entity_id>/deactivate", deactivate_factor, ["POST"])


def _add_open(bp: Blueprint, rule: str, view_func, methods: list[str]) -> None:
    bp.add_url_rule(rule, view_func=view_func, methods=methods)


def _add_auth(bp: Blueprint, rule: str, view_func, methods: list[str]) -> None:
    bp.add_url_rule(rule, view_func=auth_required(view_func), methods=methods)
