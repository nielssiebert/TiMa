from __future__ import annotations

import math
import threading
import uuid
from datetime import date, datetime, time, timedelta, timezone, tzinfo
from typing import Iterable, TypedDict
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.base import JobLookupError

from .extensions import db
from .models import (
    ExecutionEvent,
    ExecutionEventStatus,
    RecurranceType,
    Sequence,
    SequenceItem,
    Trigger,
    TriggerType,
)
from .mqtt_client import mqtt_client


_WEEKDAY_CODES = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]


class _SequenceRuntime(TypedDict):
    running_events: dict[str, str]
    pending_start_jobs: set[str]
    pending_stop_jobs: set[str]


class SchedulingService:
    def __init__(self) -> None:
        self._app = None
        self._scheduler: BackgroundScheduler | None = None
        self._tick_seconds = 1.0
        self._timezone: tzinfo = timezone.utc
        self._runtime_lock = threading.Lock()
        self._sequence_runtime: dict[str, _SequenceRuntime] = {}

    def init_app(self, app) -> None:
        if not app.config.get("SCHEDULER_ENABLED", True):
            return
        self._app = app
        self._tick_seconds = float(app.config.get("SCHEDULER_TICK_SECONDS", 1))
        self._timezone = self._resolve_timezone(app.config.get("SCHEDULER_TIMEZONE"))
        scheduler = BackgroundScheduler(timezone=self._timezone)
        scheduler.add_job(
            self._tick,
            "interval",
            seconds=self._tick_seconds,
            max_instances=1,
            coalesce=True,
            id="scheduling_tick",
        )
        scheduler.start()
        self._scheduler = scheduler

    def shutdown(self) -> None:
        if self._scheduler is None:
            return
        self._scheduler.shutdown(wait=False)
        self._scheduler = None

    def _tick(self) -> None:
        if self._app is None:
            return
        now = self._current_time()
        horizon = now + self._lookahead_delta()
        recent_window = self._recent_schedule_window()
        should_commit = False
        with self._app.app_context():
            for trigger in Trigger.query.filter_by(activated=True).all():
                if self._was_recently_scheduled(trigger, now, recent_window):
                    continue
                scheduled_any, scheduled_all = self._schedule_trigger(trigger, now, horizon)
                if scheduled_any:
                    trigger.last_scheduled = now
                    if scheduled_all and self._should_deactivate_trigger(trigger):
                        trigger.activated = False
                    should_commit = True
            if should_commit:
                db.session.commit()

    def _should_deactivate_trigger(self, trigger: Trigger) -> bool:
        if trigger.recurrance_type == RecurranceType.ONE_TIME:
            return True
        if trigger.recurrance_type == RecurranceType.TIMER and not trigger.recurring:
            return True
        return False

    def _schedule_trigger(
        self,
        trigger: Trigger,
        now: datetime,
        horizon: datetime,
    ) -> tuple[bool, bool]:
        scheduled_any = False
        scheduled_all = bool(trigger.sequences)
        for sequence in trigger.sequences:
            start_at = self._compute_sequence_start(trigger, sequence, now, horizon)
            if start_at is None:
                scheduled_all = False
                continue
            self._schedule_sequence(sequence, start_at)
            scheduled_any = True
        return scheduled_any, scheduled_all

    def _current_time(self) -> datetime:
        return datetime.now(self._timezone)

    def _resolve_timezone(self, value: str | None) -> tzinfo:
        if value:
            try:
                return ZoneInfo(value)
            except ZoneInfoNotFoundError as exc:
                raise ValueError(f"Invalid SCHEDULER_TIMEZONE: {value}") from exc
        local_timezone = datetime.now().astimezone().tzinfo
        return local_timezone if local_timezone is not None else timezone.utc

    def _lookahead_delta(self) -> timedelta:
        return timedelta(seconds=self._tick_seconds + 1)

    def _recent_schedule_window(self) -> timedelta:
        return timedelta(seconds=self._tick_seconds + 0.5)

    def _was_recently_scheduled(
        self,
        trigger: Trigger,
        now: datetime,
        window: timedelta,
    ) -> bool:
        if trigger.last_scheduled is None:
            return False
        last = trigger.last_scheduled
        if last.tzinfo is None:
            last = last.replace(tzinfo=now.tzinfo)
        if last > now:
            return False
        return now - last <= window

    def _compute_sequence_start(
        self,
        trigger: Trigger,
        sequence: Sequence,
        now: datetime,
        horizon: datetime,
    ) -> datetime | None:
        target = self._resolve_target_time(trigger, now, horizon)
        if target is None:
            return None
        if trigger.trigger_type == TriggerType.START_AT_POINT_IN_TIME:
            return target
        duration = timedelta(milliseconds=self._sequence_duration_ms(sequence))
        start = target - duration
        return start if now <= start <= horizon else None

    def _resolve_target_time(
        self,
        trigger: Trigger,
        now: datetime,
        horizon: datetime,
    ) -> datetime | None:
        if trigger.recurrance_type == RecurranceType.ONE_TIME:
            return self._resolve_one_time_target(trigger, now, horizon)
        if trigger.recurrance_type == RecurranceType.WEEKLY:
            return self._resolve_weekly_target(trigger, now, horizon)
        return self._resolve_timer_target(trigger, now, horizon)

    def _resolve_one_time_target(
        self,
        trigger: Trigger,
        now: datetime,
        horizon: datetime,
    ) -> datetime | None:
        if trigger.date is None or trigger.time is None:
            return None
        target = self._combine(trigger.date, trigger.time, now)
        return target if now <= target <= horizon else None

    def _resolve_weekly_target(
        self,
        trigger: Trigger,
        now: datetime,
        horizon: datetime,
    ) -> datetime | None:
        if trigger.time is None or not self._is_matching_weekday(trigger, now.date()):
            return None
        if not self._is_in_date_window(trigger, now.date()):
            return None
        target = self._combine(now.date(), trigger.time, now)
        return target if now <= target <= horizon else None

    def _resolve_timer_target(
        self,
        trigger: Trigger,
        now: datetime,
        horizon: datetime,
    ) -> datetime | None:
        if trigger.time is None:
            return None
        interval = self._time_to_delta(trigger.time)
        if interval.total_seconds() <= 0:
            return None
        anchor = self._timer_anchor(trigger, now)
        candidate = self._next_interval_point(anchor, now, interval)
        return candidate if candidate <= horizon else None

    def _schedule_sequence(self, sequence: Sequence, sequence_start: datetime) -> None:
        elapsed_ms = 0
        for items in self._grouped_items(sequence.sequence_items):
            group_duration = 0
            for item in items:
                for event in self._active_events(item):
                    duration_ms = self._event_duration_ms(event)
                    if not self._is_schedulable_duration(duration_ms):
                        continue
                    start_at = sequence_start + timedelta(milliseconds=elapsed_ms)
                    self._schedule_event(sequence.id, event.id, event.name, start_at, duration_ms)
                    group_duration = max(group_duration, duration_ms)
            elapsed_ms += group_duration

    def start_sequence(self, sequence: Sequence) -> None:
        self._schedule_sequence(sequence, self._current_time())

    def reset_execution_event_statuses(self) -> None:
        updated = False
        for event in ExecutionEvent.query.all():
            if event.status != ExecutionEventStatus.OFF:
                event.status = ExecutionEventStatus.OFF
                updated = True
        if updated:
            db.session.commit()

    def _schedule_event(
        self,
        sequence_id: str,
        event_id: str,
        event_name: str,
        start_at: datetime,
        duration_ms: int,
    ) -> None:
        if self._scheduler is None:
            return
        stop_at = start_at + timedelta(milliseconds=duration_ms)
        start_job_id = f"start-{uuid.uuid4()}"
        stop_job_id = f"stop-{uuid.uuid4()}"
        self._register_scheduled_jobs(sequence_id, start_job_id, stop_job_id)
        self._scheduler.add_job(
            self._run_start_job,
            "date",
            run_date=start_at,
            args=[sequence_id, event_id, event_name, start_job_id],
            id=start_job_id,
        )
        self._scheduler.add_job(
            self._run_stop_job,
            "date",
            run_date=stop_at,
            args=[sequence_id, event_id, event_name, stop_job_id],
            id=stop_job_id,
        )

    def _run_start_job(self, sequence_id: str, event_id: str, name: str, start_job_id: str) -> None:
        self._mark_event_started(sequence_id, event_id, name, start_job_id)
        self._publish(event_id, name, "START")

    def _run_stop_job(self, sequence_id: str, event_id: str, name: str, stop_job_id: str) -> None:
        stop_name = self._mark_event_stopped(sequence_id, event_id, name, stop_job_id)
        self._publish(event_id, stop_name, "STOP")

    def stop_sequence(self, sequence_id: str) -> None:
        running, jobs = self._reset_sequence_runtime(sequence_id)
        for job_id in jobs:
            self._remove_job(job_id)
        for event_id, name in running:
            self._publish(event_id, name, "STOP")

    def stop_sequences(self, sequence_ids: Iterable[str]) -> None:
        for sequence_id in set(sequence_ids):
            self.stop_sequence(sequence_id)

    def get_sequence_runtime(self, sequence_id: str) -> dict[str, object]:
        with self._runtime_lock:
            runtime = self._sequence_runtime.get(sequence_id)
            if runtime is None:
                return {
                    "is_running": False,
                    "running_execution_event_ids": [],
                    "pending_start_jobs": 0,
                    "pending_stop_jobs": 0,
                }
            running_events = runtime["running_events"]
            pending_start = runtime["pending_start_jobs"]
            pending_stop = runtime["pending_stop_jobs"]
            return {
                "is_running": bool(running_events),
                "running_execution_event_ids": sorted(running_events.keys()),
                "pending_start_jobs": len(pending_start),
                "pending_stop_jobs": len(pending_stop),
            }

    def _runtime_for(self, sequence_id: str) -> _SequenceRuntime:
        runtime = self._sequence_runtime.get(sequence_id)
        if runtime is None:
            runtime = _SequenceRuntime(
                running_events={},
                pending_start_jobs=set(),
                pending_stop_jobs=set(),
            )
            self._sequence_runtime[sequence_id] = runtime
        return runtime

    def _register_scheduled_jobs(self, sequence_id: str, start_job_id: str, stop_job_id: str) -> None:
        with self._runtime_lock:
            runtime = self._runtime_for(sequence_id)
            runtime["pending_start_jobs"].add(start_job_id)
            runtime["pending_stop_jobs"].add(stop_job_id)

    def _mark_event_started(self, sequence_id: str, event_id: str, name: str, start_job_id: str) -> None:
        with self._runtime_lock:
            runtime = self._runtime_for(sequence_id)
            runtime["pending_start_jobs"].discard(start_job_id)
            runtime["running_events"][event_id] = name

    def _mark_event_stopped(
        self,
        sequence_id: str,
        event_id: str,
        fallback_name: str,
        stop_job_id: str,
    ) -> str:
        with self._runtime_lock:
            runtime = self._runtime_for(sequence_id)
            runtime["pending_stop_jobs"].discard(stop_job_id)
            name = runtime["running_events"].pop(event_id, fallback_name)
            self._cleanup_runtime(sequence_id, runtime)
            return name

    def _reset_sequence_runtime(self, sequence_id: str) -> tuple[list[tuple[str, str]], set[str]]:
        with self._runtime_lock:
            runtime = self._sequence_runtime.pop(sequence_id, None)
            if runtime is None:
                return [], set()
            running = list(runtime["running_events"].items())
            jobs = set(runtime["pending_start_jobs"]) | set(runtime["pending_stop_jobs"])
            return running, jobs

    def _cleanup_runtime(self, sequence_id: str, runtime: _SequenceRuntime) -> None:
        if runtime["running_events"]:
            return
        if runtime["pending_start_jobs"] or runtime["pending_stop_jobs"]:
            return
        self._sequence_runtime.pop(sequence_id, None)

    def _remove_job(self, job_id: str) -> None:
        if self._scheduler is None:
            return
        try:
            self._scheduler.remove_job(job_id)
        except JobLookupError:
            return

    def _publish(self, entity_id: str, name: str, action: str) -> None:
        if self._app is None:
            return
        with self._app.app_context():
            try:
                mqtt_client.publish_execution_event(entity_id, name, action)
            except RuntimeError as exc:
                self._app.logger.error("Unable to publish scheduled message: %s", exc)

    def _sequence_duration_ms(self, sequence: Sequence) -> int:
        total_ms = 0
        for items in self._grouped_items(sequence.sequence_items):
            total_ms += self._group_duration_ms(items)
        return total_ms

    def _group_duration_ms(self, items: Iterable[SequenceItem]) -> int:
        durations: list[int] = []
        for item in items:
            for event in self._active_events(item):
                duration_ms = self._event_duration_ms(event)
                if self._is_schedulable_duration(duration_ms):
                    durations.append(duration_ms)
        return max(durations, default=0)

    def _grouped_items(self, sequence_items: list[SequenceItem]) -> list[list[SequenceItem]]:
        grouped: dict[int, list[SequenceItem]] = {}
        for item in sequence_items:
            grouped.setdefault(item.order, []).append(item)
        return [grouped[o] for o in sorted(grouped.keys())]

    def _active_events(self, item: SequenceItem):
        if item.execution_event is not None:
            return [item.execution_event] if item.execution_event.activated else []
        if item.execution_event_group is None:
            return []
        return [event for event in item.execution_event_group.execution_events if event.activated]

    def _event_duration_ms(self, event) -> int:
        factor = 1.0
        for entity_factor in event.factors:
            if not entity_factor.activated:
                continue
            factor *= entity_factor.factor
        return int(event.duration_ms * factor)

    def _is_schedulable_duration(self, duration_ms: int) -> bool:
        return duration_ms > 1

    def _combine(self, d: date, t: time, reference: datetime) -> datetime:
        return datetime.combine(d, t, tzinfo=reference.tzinfo)

    def _time_to_delta(self, value: time) -> timedelta:
        return timedelta(hours=value.hour, minutes=value.minute, seconds=value.second)

    def _timer_anchor(self, trigger: Trigger, now: datetime) -> datetime:
        anchor_date = trigger.date or now.date()
        return self._combine(anchor_date, time.min, now)

    def _next_interval_point(
        self,
        anchor: datetime,
        now: datetime,
        interval: timedelta,
    ) -> datetime:
        if now <= anchor:
            return anchor
        elapsed = (now - anchor).total_seconds() / interval.total_seconds()
        return anchor + interval * math.ceil(elapsed)

    def _is_matching_weekday(self, trigger: Trigger, current_date: date) -> bool:
        if not trigger.weekdays:
            return False
        days = {item.strip() for item in trigger.weekdays.split(",") if item.strip()}
        return _WEEKDAY_CODES[current_date.weekday()] in days

    def _is_in_date_window(self, trigger: Trigger, current_date: date) -> bool:
        if trigger.from_date and current_date < trigger.from_date:
            return False
        if trigger.to_date and current_date > trigger.to_date:
            return False
        return True

scheduling_service = SchedulingService()
