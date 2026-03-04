from __future__ import annotations

from flask import Blueprint

from .routes import register_routes

api_bp = Blueprint("api", __name__, url_prefix="/api")

register_routes(api_bp)

__all__ = ["api_bp"]
