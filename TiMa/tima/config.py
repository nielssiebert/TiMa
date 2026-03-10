from __future__ import annotations

import os
from dataclasses import dataclass


def _get_env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    return value if value is not None else default


def _get_env_tuple(name: str, default: str) -> tuple[str, ...]:
    value = _get_env(name, default) or default
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _normalize_api_prefix(value: str | None) -> str:
    if value is None:
        return "/api"
    trimmed = value.strip()
    if not trimmed:
        return "/api"
    if trimmed == "/":
        return "/"
    prefixed = trimmed if trimmed.startswith("/") else f"/{trimmed}"
    return prefixed.rstrip("/")


@dataclass(frozen=True)
class Config:
    # Core
    APP_NAME: str = _get_env("APP_NAME", "TiMa")
    ENV: str = _get_env("FLASK_ENV", "production")
    SECRET_KEY: str = _get_env("SECRET_KEY", "change-me")
    BASIC_AUTH_ENABLED: bool = _get_env("BASIC_AUTH_ENABLED", "false").lower() == "true"
    MQTT_ENABLED: bool = _get_env("MQTT_ENABLED", "true").lower() == "true"
    SCHEDULER_ENABLED: bool = _get_env("SCHEDULER_ENABLED", "true").lower() == "true"

    # Database
    DB_PATH: str = _get_env("DB_PATH", "tima.sqlite")
    SQLALCHEMY_DATABASE_URI: str = _get_env(
        "DATABASE_URL", f"sqlite:///{DB_PATH}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

    # MQTT / Mosquitto
    MQTT_BROKER_HOST: str = _get_env("MQTT_BROKER_HOST", "localhost")
    MQTT_BROKER_PORT: int = int(_get_env("MQTT_BROKER_PORT", "1883"))
    MQTT_CLIENT_ID: str = _get_env("MQTT_CLIENT_ID", "tima-backend")
    MQTT_USERNAME: str | None = _get_env("MQTT_USERNAME")
    MQTT_PASSWORD: str | None = _get_env("MQTT_PASSWORD")

    MQTT_TOPIC_EXECUTION_EVENTS: str = _get_env(
        "MQTT_TOPIC_EXECUTION_EVENTS", "tima/execution-events"
    )
    MQTT_TOPIC_EXECUTION_ACKS: str = _get_env(
        "MQTT_TOPIC_EXECUTION_ACKS", "tima/execution-events/acks"
    )
    MQTT_TOPIC_FACTORS: str = _get_env(
        "MQTT_TOPIC_FACTORS", "tima/factors"
    )
    MQTT_TOPIC_FACTORS_VALUES: str = _get_env(
        "MQTT_TOPIC_FACTORS_VALUES", "tima/factors/values"
    )

    # Scheduler
    SCHEDULER_TICK_SECONDS: int = int(_get_env("SCHEDULER_TICK_SECONDS", "30"))

    # Message retention in days
    MESSAGE_RETENTION_DAYS: int = int(_get_env("MESSAGE_RETENTION_DAYS", "30"))

    # API
    API_URL_PREFIX: str = _normalize_api_prefix(_get_env("API_URL_PREFIX", "/api"))
    AUTH_CACHE_TTL_SECONDS: float = float(_get_env("AUTH_CACHE_TTL_SECONDS", "150"))
    AUTH_CACHE_MAX_SIZE: int = int(_get_env("AUTH_CACHE_MAX_SIZE", "256"))

    # CORS
    CORS_ALLOWED_ORIGINS: tuple[str, ...] = _get_env_tuple(
        "CORS_ALLOWED_ORIGINS", "http://0.0.0.0"
    )
