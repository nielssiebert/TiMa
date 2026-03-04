from __future__ import annotations

from flask import Flask
from flask_cors import CORS

from .config import Config
from .extensions import db
from .mqtt_client import mqtt_client
from .scheduling import scheduling_service
from .api import create_api_blueprint


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config())
    api_url_prefix = app.config.get("API_URL_PREFIX", "/api")
    _configure_cors(app, api_url_prefix)

    db.init_app(app)
    if app.config.get("MQTT_ENABLED", True):
        mqtt_client.init_app(app)
    scheduling_service.init_app(app)
    app.register_blueprint(create_api_blueprint(api_url_prefix))

    with app.app_context():
        db.create_all()
        scheduling_service.reset_execution_event_statuses()

    return app


def _configure_cors(app: Flask, api_url_prefix: str) -> None:
    normalized_prefix = _normalize_prefix(api_url_prefix)
    CORS(
        app,
        resources={
            rf"{normalized_prefix}/*": {
                "origins": app.config["CORS_ALLOWED_ORIGINS"]
            }
        },
    )


def _normalize_prefix(prefix: str) -> str:
    if not prefix or prefix == "/":
        return ""
    return prefix.rstrip("/")
