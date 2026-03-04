from __future__ import annotations

from datetime import date, datetime, time
from typing import Any


def parse_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return _parse_date_from_string(value)
    raise ValueError("Invalid date")


def parse_time(value: Any) -> time | None:
    if value is None:
        return None
    if isinstance(value, time):
        return value
    if isinstance(value, str):
        return time.fromisoformat(value)
    raise ValueError("Invalid time")


def normalize_weekdays(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, list):
        return _normalize_weekday_list(value)
    if isinstance(value, str):
        return _normalize_weekday_string(value)
    raise ValueError("Invalid weekdays")


def _parse_date_from_string(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        return datetime.strptime(value, "%d.%m.%Y").date()


def _normalize_weekday_list(value: list[Any]) -> str:
    days = [str(v).upper() for v in value]
    _validate_weekdays(days)
    return ",".join(days)


def _normalize_weekday_string(value: str) -> str:
    days = [v.strip().upper() for v in value.split(",") if v.strip()]
    _validate_weekdays(days)
    return ",".join(days)


def _validate_weekdays(days: list[str]) -> None:
    allowed = {"SU", "MO", "TU", "WE", "TH", "FR", "SA"}
    if not days:
        raise ValueError("weekdays must not be empty")
    invalid = [day for day in days if day not in allowed]
    if invalid:
        raise ValueError("weekdays must be one of SU, MO, TU, WE, TH, FR, SA")
