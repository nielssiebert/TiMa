from __future__ import annotations

import base64
import time
from dataclasses import dataclass
from functools import wraps
from threading import Lock
from typing import Callable

from flask import current_app, jsonify, request
from werkzeug.security import check_password_hash

from ..models import User


@dataclass(frozen=True)
class _AuthCacheEntry:
    username: str
    confirmed: bool
    expires_at: float


_AUTH_CACHE: dict[str, _AuthCacheEntry] = {}
_AUTH_CACHE_LOCK = Lock()


def auth_required(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_app.config.get("BASIC_AUTH_ENABLED", True):
            return func(*args, **kwargs)
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Basic "):
            return unauthorized()
        if not _is_authorized_auth(auth):
            return unauthorized()
        return func(*args, **kwargs)

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


def invalidate_auth_cache_for_user(username: str) -> None:
    with _AUTH_CACHE_LOCK:
        matching_headers = [
            header
            for header, entry in _AUTH_CACHE.items()
            if entry.username == username
        ]
        for header in matching_headers:
            _AUTH_CACHE.pop(header, None)


def _is_authorized_auth(auth_header: str) -> bool:
    cached = _get_cached_auth_entry(auth_header)
    if cached is not None:
        return cached.confirmed

    credentials = _decode_basic_credentials(auth_header)
    if credentials is None:
        return False

    username, password = credentials
    user = User.query.filter_by(username=username).first()
    if user is None or not check_password_hash(user.password_hash, password):
        return False

    _store_cached_auth_entry(auth_header, username, user.confirmed)
    return user.confirmed


def _decode_basic_credentials(auth_header: str) -> tuple[str, str] | None:
    try:
        decoded = base64.b64decode(auth_header.split(" ", 1)[1]).decode("utf-8")
        return decoded.split(":", 1)
    except Exception:
        return None


def _get_cached_auth_entry(auth_header: str) -> _AuthCacheEntry | None:
    now = time.monotonic()
    with _AUTH_CACHE_LOCK:
        entry = _AUTH_CACHE.get(auth_header)
        if entry is None:
            return None
        if entry.expires_at <= now:
            _AUTH_CACHE.pop(auth_header, None)
            return None
        return entry


def _store_cached_auth_entry(auth_header: str, username: str, confirmed: bool) -> None:
    ttl = float(current_app.config.get("AUTH_CACHE_TTL_SECONDS", 15.0))
    if ttl <= 0:
        return

    now = time.monotonic()
    entry = _AuthCacheEntry(
        username=username,
        confirmed=confirmed,
        expires_at=now + ttl,
    )
    max_size = int(current_app.config.get("AUTH_CACHE_MAX_SIZE", 256))
    with _AUTH_CACHE_LOCK:
        _purge_expired_auth_entries(now)
        _AUTH_CACHE.pop(auth_header, None)
        _AUTH_CACHE[auth_header] = entry
        while len(_AUTH_CACHE) > max_size:
            _AUTH_CACHE.pop(next(iter(_AUTH_CACHE)))


def _purge_expired_auth_entries(now: float) -> None:
    expired_headers = [
        header
        for header, entry in _AUTH_CACHE.items()
        if entry.expires_at <= now
    ]
    for header in expired_headers:
        _AUTH_CACHE.pop(header, None)
