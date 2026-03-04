from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from tima.extensions import db
from tima.mqtt_client import mqtt_client
from tima.models import (
    ExecutionEvent,
    ExecutionEventGroup,
    Factor,
    Sequence,
    SequenceItem,
    Trigger,
)


@pytest.fixture()
def app(monkeypatch, tmp_path_factory, mqtt_mode):
    db_path = _create_test_db_path(tmp_path_factory)
    db_url = _sqlite_url(db_path)
    mqtt_enabled = "true" if mqtt_mode else "false"
    monkeypatch.setenv("BASIC_AUTH_ENABLED", "false")
    monkeypatch.setenv("MQTT_ENABLED", mqtt_enabled)
    monkeypatch.setenv("SCHEDULER_ENABLED", "false")
    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("DB_PATH", str(db_path))
    app = _create_test_app()
    if not mqtt_mode:
        _stub_mqtt(app)
    app.config.update(
        TESTING=True,
        BASIC_AUTH_ENABLED=False,
        MQTT_ENABLED=False,
        SCHEDULER_ENABLED=False,
        SQLALCHEMY_DATABASE_URI=db_url,
        DATABASE_URL=db_url,
    )

    with app.app_context():
        db.drop_all()
        db.create_all()
        _cleanup_entities()
        yield app


@pytest.fixture()
def client(app):
    return app.test_client()


def _cleanup_entities() -> None:
    ids = {"test_id_1", "test_id_2", "test_id_3"}
    SequenceItem.query.delete()
    Trigger.query.filter(Trigger.id.in_(ids)).delete()
    Sequence.query.filter(Sequence.id.in_(ids)).delete()
    ExecutionEventGroup.query.filter(ExecutionEventGroup.id.in_(ids)).delete()
    ExecutionEvent.query.filter(ExecutionEvent.id.in_(ids)).delete()
    Factor.query.filter(Factor.id.in_(ids)).delete()
    db.session.commit()


@pytest.fixture()
def mqtt_mode(request) -> bool:
    return request.node.get_closest_marker("real_mqtt") is not None


def _create_test_app():
    import tima
    import tima.config

    importlib.reload(tima.config)
    importlib.reload(tima)
    return tima.create_app()


class _MqttStub:
    def __init__(self) -> None:
        self.published: list[tuple[str, str]] = []

    def publish(self, *_args, **_kwargs):
        if _args:
            topic = str(_args[0])
            payload = str(_args[1]) if len(_args) > 1 else ""
            self.published.append((topic, payload))
        return None


def _stub_mqtt(app) -> None:
    mqtt_client._client = _MqttStub()
    mqtt_client._app = app


def _create_test_db_path(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("db") / "test.db"


def _sqlite_url(path: Path) -> str:
    return f"sqlite:///{path}"
