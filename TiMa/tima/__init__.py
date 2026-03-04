from __future__ import annotations

from flask import Flask
from flask_cors import CORS

from .config import Config
from .extensions import db
from .mqtt_client import mqtt_client
from .scheduling import scheduling_service
from .api import api_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config())
    _configure_cors(app)

    db.init_app(app)
    if app.config.get("MQTT_ENABLED", True):
        mqtt_client.init_app(app)
    scheduling_service.init_app(app)
    app.register_blueprint(api_bp)

    with app.app_context():
        db.create_all()
        scheduling_service.reset_execution_event_statuses()

    return app


def _configure_cors(app: Flask) -> None:
    CORS(
        app,
        resources={r"/api/*": {"origins": app.config["CORS_ALLOWED_ORIGINS"]}},
    )
