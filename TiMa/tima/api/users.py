from __future__ import annotations

import base64
from typing import Any

from flask import jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db
from ..models import User
from .common import validation_error
from .serializers import serialize_user


_PASSWORD_HASH_METHOD = "pbkdf2:sha256"


def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return validation_error("username and password are required")

    user = User.query.filter_by(username=username).first()
    if user is None or not check_password_hash(user.password_hash, password):
        return validation_error("Invalid credentials", status_code=401)

    return jsonify({"message": "ok"})


def create_user():
    data = request.get_json(silent=True) or {}
    user_id = data.get("id")
    username = data.get("username")
    password = data.get("password")

    error = _validate_user_payload(user_id, username, password)
    if error:
        return error

    if db.session.get(User, user_id) is not None:
        return validation_error("id already exists")
    if User.query.filter_by(username=username).first() is not None:
        return validation_error("username must be unique")

    user = User(
        id=user_id,
        username=username,
        password_hash=generate_password_hash(password, method=_PASSWORD_HASH_METHOD),
        confirmed=_is_first_user(),
    )
    db.session.add(user)
    db.session.commit()
    return jsonify(serialize_user(user)), 201


def get_users():
    users = User.query.order_by(User.username.asc()).all()
    return jsonify([serialize_user(user) for user in users])


def confirm_user(entity_id: str):
    user = db.session.get(User, entity_id)
    if user is None:
        return validation_error("User not found", status_code=404)
    user.confirmed = True
    db.session.commit()
    return jsonify(serialize_user(user))


def change_password():
    data = request.get_json(silent=True) or {}
    old_password = data.get("old_password")
    new_password = data.get("new_password")
    if not old_password or not new_password:
        return validation_error("old_password and new_password are required")

    user, error = _get_user_from_auth()
    if error:
        return error
    if user is None or not check_password_hash(user.password_hash, old_password):
        return validation_error("Invalid credentials", status_code=401)

    user.password_hash = generate_password_hash(
        new_password,
        method=_PASSWORD_HASH_METHOD,
    )
    db.session.commit()
    return jsonify({"message": "ok"})


def _validate_user_payload(user_id: Any, username: Any, password: Any):
    if not user_id:
        return validation_error("id is required")
    if not username:
        return validation_error("username is required")
    if not password:
        return validation_error("password is required")
    return None


def _get_user_from_auth() -> tuple[User | None, Any | None]:
    auth = request.headers.get("Authorization", "")
    try:
        decoded = base64.b64decode(auth.split(" ", 1)[1]).decode("utf-8")
        username, _ = decoded.split(":", 1)
    except Exception:
        return None, validation_error("Invalid credentials", status_code=401)

    user = User.query.filter_by(username=username).first()
    if user is None:
        return None, validation_error("Invalid credentials", status_code=401)
    return user, None


def _is_first_user() -> bool:
    return User.query.count() == 0
