from __future__ import annotations

from flask import Blueprint

from .routes import register_routes


def create_api_blueprint(url_prefix: str = "/api") -> Blueprint:
    api_bp = Blueprint("api", __name__, url_prefix=url_prefix)
    register_routes(api_bp)
    return api_bp


__all__ = ["create_api_blueprint"]
