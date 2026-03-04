from __future__ import annotations

import base64
from typing import Callable

from flask import current_app, jsonify, request
from werkzeug.security import check_password_hash

from ..models import User


def auth_required(func: Callable) -> Callable:
    def wrapper(*args, **kwargs):
        if not current_app.config.get("BASIC_AUTH_ENABLED", True):
            return func(*args, **kwargs)
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Basic "):
            return unauthorized()
        user = _get_user_from_auth(auth)
        if user is None or not user.confirmed:
            return unauthorized()
        return func(*args, **kwargs)

    wrapper.__name__ = func.__name__
    return wrapper


def unauthorized():
    return (
        jsonify({"error": "validationError", "message": "Unauthorized"}),
        401,
        {"WWW-Authenticate": 'Basic realm="TiMa"'},
    )


def validation_error(message: str, status_code: int = 400):
    return jsonify({"error": "validationError", "message": message}), status_code


def unexpected_error(message: str):
    return jsonify({"error": "unexpectedError", "message": message}), 500


def _get_user_from_auth(auth_header: str) -> User | None:
    try:
        decoded = base64.b64decode(auth_header.split(" ", 1)[1]).decode("utf-8")
        username, password = decoded.split(":", 1)
    except Exception:
        return None

    user = User.query.filter_by(username=username).first()
    if user is None or not check_password_hash(user.password_hash, password):
        return None
    return user
