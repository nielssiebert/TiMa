from __future__ import annotations

import base64
import importlib
from pathlib import Path

import pytest

from tima.extensions import db


@pytest.fixture()
def auth_app(monkeypatch, tmp_path_factory):
    db_path = _create_test_db_path(tmp_path_factory)
    db_url = _sqlite_url(db_path)
    monkeypatch.setenv("BASIC_AUTH_ENABLED", "true")
    monkeypatch.setenv("MQTT_ENABLED", "false")
    monkeypatch.setenv("SCHEDULER_ENABLED", "false")
    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("DB_PATH", str(db_path))

    app = _create_test_app()
    app.config.update(
        TESTING=True,
        BASIC_AUTH_ENABLED=True,
        AUTH_CACHE_TTL_SECONDS=30,
        AUTH_CACHE_MAX_SIZE=256,
        MQTT_ENABLED=False,
        SCHEDULER_ENABLED=False,
        SQLALCHEMY_DATABASE_URI=db_url,
        DATABASE_URL=db_url,
    )

    with app.app_context():
        db.drop_all()
        db.create_all()
        yield app


@pytest.fixture()
def auth_client(auth_app):
    return auth_app.test_client()


def test_first_user_is_auto_confirmed(auth_client):
    response = auth_client.post(
        "/api/users",
        json={"id": "u1", "username": "admin", "password": "secret"},
    )
    assert response.status_code == 201
    assert response.get_json()["confirmed"] is True


def test_unconfirmed_user_cannot_access_restricted_apis(auth_client):
    auth_client.post(
        "/api/users",
        json={"id": "u1", "username": "admin", "password": "secret"},
    )
    admin_auth = _basic_auth("admin", "secret")

    create_response = auth_client.post(
        "/api/users",
        json={"id": "u2", "username": "user2", "password": "secret2"},
        headers=admin_auth,
    )
    assert create_response.status_code == 201
    assert create_response.get_json()["confirmed"] is False

    user_auth = _basic_auth("user2", "secret2")
    list_response = auth_client.get("/api/users", headers=user_auth)
    assert list_response.status_code == 401

    factors_response = auth_client.get("/api/factors", headers=user_auth)
    assert factors_response.status_code == 401


def test_user_registration_is_open_without_auth(auth_client):
    first_response = auth_client.post(
        "/api/users",
        json={"id": "u1", "username": "admin", "password": "secret"},
    )
    assert first_response.status_code == 201

    second_response = auth_client.post(
        "/api/users",
        json={"id": "u2", "username": "user2", "password": "secret2"},
    )
    assert second_response.status_code == 201
    assert second_response.get_json()["confirmed"] is False


def test_user_registration_preflight_allows_frontend_origin(auth_app, auth_client):
    frontend_origin = auth_app.config["CORS_ALLOWED_ORIGINS"][0]
    response = auth_client.options(
        "/api/users",
        headers={
            "Origin": frontend_origin,
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers.get("Access-Control-Allow-Origin") == frontend_origin


def test_confirmed_user_can_confirm_other_user_and_access_restricted_apis(auth_client):
    auth_client.post(
        "/api/users",
        json={"id": "u1", "username": "admin", "password": "secret"},
    )
    admin_auth = _basic_auth("admin", "secret")
    auth_client.post(
        "/api/users",
        json={"id": "u2", "username": "user2", "password": "secret2"},
        headers=admin_auth,
    )

    users_before = auth_client.get("/api/users", headers=admin_auth)
    assert users_before.status_code == 200
    confirmed_map = {u["id"]: u["confirmed"] for u in users_before.get_json()}
    assert confirmed_map == {"u1": True, "u2": False}

    confirm_response = auth_client.post("/api/users/u2/confirm", headers=admin_auth)
    assert confirm_response.status_code == 200
    assert confirm_response.get_json()["confirmed"] is True

    user_auth = _basic_auth("user2", "secret2")
    factors_response = auth_client.get("/api/factors", headers=user_auth)
    assert factors_response.status_code == 200


def test_change_password_updates_credentials(auth_client):
    auth_client.post(
        "/api/users",
        json={"id": "u1", "username": "admin", "password": "secret"},
    )

    change_response = auth_client.post(
        "/api/users/change_password",
        json={"old_password": "secret", "new_password": "new-secret"},
        headers=_basic_auth("admin", "secret"),
    )

    assert change_response.status_code == 200
    assert change_response.get_json()["message"] == "ok"

    old_login_response = auth_client.post(
        "/api/login",
        json={"username": "admin", "password": "secret"},
    )
    assert old_login_response.status_code == 401

    new_login_response = auth_client.post(
        "/api/login",
        json={"username": "admin", "password": "new-secret"},
    )
    assert new_login_response.status_code == 200


def test_change_password_requires_valid_old_password(auth_client):
    auth_client.post(
        "/api/users",
        json={"id": "u1", "username": "admin", "password": "secret"},
    )

    response = auth_client.post(
        "/api/users/change_password",
        json={"old_password": "wrong", "new_password": "new-secret"},
        headers=_basic_auth("admin", "secret"),
    )

    assert response.status_code == 401


def test_change_password_requires_payload_fields(auth_client):
    auth_client.post(
        "/api/users",
        json={"id": "u1", "username": "admin", "password": "secret"},
    )

    response = auth_client.post(
        "/api/users/change_password",
        json={"old_password": "secret"},
        headers=_basic_auth("admin", "secret"),
    )

    assert response.status_code == 400


def test_basic_auth_uses_short_lived_cache(auth_client, monkeypatch):
    import tima.api.common as api_common

    auth_client.post(
        "/api/users",
        json={"id": "u1", "username": "admin", "password": "secret"},
    )
    auth_header = _basic_auth("admin", "secret")

    no_auth = auth_client.get("/api/factors")
    first = auth_client.get("/api/factors", headers=auth_header)

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("check_password_hash should not run for cached auth")

    monkeypatch.setattr(api_common, "check_password_hash", fail_if_called)
    second = auth_client.get("/api/factors", headers=auth_header)

    assert no_auth.status_code == 401
    assert first.status_code == 200
    assert second.status_code == 200


def test_password_change_invalidates_auth_cache(auth_client):
    auth_client.post(
        "/api/users",
        json={"id": "u1", "username": "admin", "password": "secret"},
    )

    old_auth = _basic_auth("admin", "secret")
    auth_client.get("/api/factors", headers=old_auth)

    change_response = auth_client.post(
        "/api/users/change_password",
        json={"old_password": "secret", "new_password": "new-secret"},
        headers=old_auth,
    )

    old_access = auth_client.get("/api/factors", headers=old_auth)
    new_access = auth_client.get("/api/factors", headers=_basic_auth("admin", "new-secret"))

    assert change_response.status_code == 200
    assert old_access.status_code == 401
    assert new_access.status_code == 200


def _basic_auth(username: str, password: str) -> dict[str, str]:
    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("utf-8")
    return {"Authorization": f"Basic {token}"}


def _create_test_app():
    import tima
    import tima.config

    importlib.reload(tima.config)
    importlib.reload(tima)
    return tima.create_app()


def _create_test_db_path(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("auth_db") / "test.db"


def _sqlite_url(path: Path) -> str:
    return f"sqlite:///{path}"
