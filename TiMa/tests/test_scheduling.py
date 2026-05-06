from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from tima.extensions import db
from tima.models import (
    ExecutionEvent,
    ExecutionEventStatus,
    Factor,
    RecurranceType,
    Sequence,
    SequenceItem,
    Trigger,
    TriggerType,
)
from tima.scheduling import SchedulingService


def test_sequence_duration_respects_parallel_orders_and_factors():
    service = SchedulingService()
    event1 = _event("event_1", 1000, 2.0)
    event2 = _event("event_2", 3000, 1.0)
    sequence = Sequence(id="seq", name="seq")
    sequence.sequence_items = [
        _item("item_1", 1, event1),
        _item("item_2", 1, event2),
        _item("item_3", 2, event1),
    ]

    assert service._sequence_duration_ms(sequence) == 5000


def test_stop_trigger_start_time_subtracts_sequence_duration():
    service = SchedulingService()
    now = datetime(2026, 2, 28, 21, 0, 0, tzinfo=timezone.utc)
    target = now + timedelta(seconds=4)
    trigger = Trigger(
        id="trigger_1",
        name="trigger_1",
        trigger_type=TriggerType.STOP_AT_POINT_IN_TIME,
        recurrance_type=RecurranceType.ONE_TIME,
        date=target.date(),
        time=target.time().replace(microsecond=0),
        activated=True,
    )
    sequence = Sequence(id="seq", name="seq")
    sequence.sequence_items = [_item("item_1", 1, _event("event_1", 3000, 1.0))]

    start_at = service._compute_sequence_start(trigger, sequence, now, now + timedelta(seconds=5))

    assert start_at == target - timedelta(seconds=3)


def test_stop_trigger_uses_sequence_start_window_not_stop_target_window():
    service = SchedulingService()
    now = datetime(2026, 2, 28, 21, 58, 0, tzinfo=timezone.utc)
    horizon = now + timedelta(seconds=31)
    target = now + timedelta(minutes=2)
    trigger = Trigger(
        id="trigger_stop_window",
        name="trigger_stop_window",
        trigger_type=TriggerType.STOP_AT_POINT_IN_TIME,
        recurrance_type=RecurranceType.ONE_TIME,
        date=target.date(),
        time=target.time().replace(microsecond=0),
        activated=True,
    )
    sequence = Sequence(id="seq_stop_window", name="seq_stop_window")
    sequence.sequence_items = [_item("item_stop_window", 1, _event("event_stop_window", 120000, 1.0))]

    start_at = service._compute_sequence_start(trigger, sequence, now, horizon)

    assert start_at == now


def test_timer_target_uses_next_interval_point():
    service = SchedulingService()
    now = datetime(2026, 2, 28, 0, 0, 21, tzinfo=timezone.utc)
    trigger = Trigger(
        id="trigger_2",
        name="trigger_2",
        trigger_type=TriggerType.START_AT_POINT_IN_TIME,
        recurrance_type=RecurranceType.TIMER,
        date=date(2026, 2, 28),
        time=time(0, 0, 10),
        activated=True,
    )

    target = service._resolve_timer_target(trigger, now, now + timedelta(seconds=12))

    assert target == datetime(2026, 2, 28, 0, 0, 30, tzinfo=timezone.utc)


def test_tick_windows_follow_scheduler_tick_seconds():
    service = SchedulingService()
    service._tick_seconds = 2.0

    assert service._lookahead_delta() == timedelta(seconds=3)
    assert service._recent_schedule_window() == timedelta(seconds=2.5)


def test_init_app_uses_configured_scheduler_timezone(app, monkeypatch):
    service = SchedulingService()
    created: dict[str, object] = {}

    class _SchedulerInitStub:
        def __init__(self, *args, **kwargs) -> None:
            _ = args
            created["timezone"] = kwargs.get("timezone")

        def add_job(self, *_args, **_kwargs) -> None:
            return None

        def start(self) -> None:
            created["started"] = True

    app.config.update(
        SCHEDULER_ENABLED=True,
        SCHEDULER_TICK_SECONDS=30,
        SCHEDULER_TIMEZONE="Europe/Berlin",
    )

    monkeypatch.setattr("tima.scheduling.BackgroundScheduler", _SchedulerInitStub)

    service.init_app(app)

    assert created["started"] is True
    assert created["timezone"] == ZoneInfo("Europe/Berlin")
    assert service._current_time().tzinfo == ZoneInfo("Europe/Berlin")


def test_recently_scheduled_window_check():
    service = SchedulingService()
    now = datetime(2026, 2, 28, 21, 0, 0, tzinfo=timezone.utc)
    window = timedelta(seconds=1.5)
    trigger = Trigger(
        id="trigger_window",
        name="trigger_window",
        trigger_type=TriggerType.START_AT_POINT_IN_TIME,
        recurrance_type=RecurranceType.ONE_TIME,
        activated=True,
    )

    trigger.last_scheduled = now - timedelta(seconds=1.4)
    assert service._was_recently_scheduled(trigger, now, window)

    trigger.last_scheduled = now - timedelta(seconds=1.6)
    assert not service._was_recently_scheduled(trigger, now, window)


def test_tick_persists_last_scheduled_and_skips_duplicate(app, monkeypatch):
    service = SchedulingService()
    service._app = app
    service._tick_seconds = 1.0
    now = datetime(2026, 2, 28, 21, 0, 0, tzinfo=timezone.utc)
    scheduled_starts: list[datetime] = []
    current_times = [now, now + timedelta(milliseconds=400)]

    with app.app_context():
        _persist_tick_trigger(now + timedelta(seconds=1))

    monkeypatch.setattr(service, "_current_time", lambda: current_times.pop(0))
    monkeypatch.setattr(service, "_schedule_sequence", lambda _sequence, start_at: scheduled_starts.append(start_at))

    service._tick()
    service._tick()

    with app.app_context():
        trigger = db.session.get(Trigger, "trigger_tick")
        assert trigger is not None
        assert trigger.last_scheduled is not None
        persisted = trigger.last_scheduled.replace(tzinfo=timezone.utc)
        assert persisted == now
        assert trigger.activated is False

    assert len(scheduled_starts) == 1


def test_sequence_duration_skips_events_with_duration_at_most_one_ms():
    service = SchedulingService()
    event_skipped = _event("event_skipped", 1000, 0.001)
    event_counted = _event("event_counted", 3000, 1.0)
    sequence = Sequence(id="seq_small_duration", name="seq_small_duration")
    sequence.sequence_items = [
        _item("item_1", 1, event_skipped),
        _item("item_2", 2, event_counted),
    ]

    assert service._sequence_duration_ms(sequence) == 3000


def test_sequence_duration_ignores_deactivated_factors():
    service = SchedulingService()
    event = _event("event_inactive_factor", 1000, 2.0, factor_activated=False)
    sequence = Sequence(id="seq_inactive_factor", name="seq_inactive_factor")
    sequence.sequence_items = [_item("item_1", 1, event)]

    assert service._sequence_duration_ms(sequence) == 1000


def test_tick_deactivates_non_recurring_timer_trigger(app, monkeypatch):
    service = SchedulingService()
    service._app = app
    service._tick_seconds = 1.0
    now = datetime(2026, 2, 28, 0, 0, 9, tzinfo=timezone.utc)

    with app.app_context():
        _persist_tick_trigger(now, recurrance_type=RecurranceType.TIMER, recurring=False)

    monkeypatch.setattr(service, "_current_time", lambda: now)
    monkeypatch.setattr(service, "_schedule_sequence", lambda _sequence, _start_at: None)
    service._tick()

    with app.app_context():
        trigger = db.session.get(Trigger, "trigger_tick")
        assert trigger is not None
        assert trigger.activated is False


def test_tick_keeps_recurring_timer_trigger_active(app, monkeypatch):
    service = SchedulingService()
    service._app = app
    service._tick_seconds = 1.0
    now = datetime(2026, 2, 28, 0, 0, 9, tzinfo=timezone.utc)

    with app.app_context():
        _persist_tick_trigger(now, recurrance_type=RecurranceType.TIMER, recurring=True)

    monkeypatch.setattr(service, "_current_time", lambda: now)
    monkeypatch.setattr(service, "_schedule_sequence", lambda _sequence, _start_at: None)
    service._tick()

    with app.app_context():
        trigger = db.session.get(Trigger, "trigger_tick")
        assert trigger is not None
        assert trigger.activated is True


def test_tick_keeps_one_time_trigger_active_when_only_some_sequences_schedule(app, monkeypatch):
    service = SchedulingService()
    service._app = app
    service._tick_seconds = 1.0
    now = datetime(2026, 2, 28, 21, 0, 0, tzinfo=timezone.utc)

    with app.app_context():
        trigger_id = _persist_trigger_with_multiple_sequences(
            now + timedelta(seconds=2),
            [500, 3000],
        )

    monkeypatch.setattr(service, "_current_time", lambda: now)
    monkeypatch.setattr(service, "_schedule_sequence", lambda _sequence, _start_at: None)

    service._tick()

    with app.app_context():
        persisted = db.session.get(Trigger, trigger_id)
        assert persisted is not None
        assert persisted.activated is True


def test_schedule_sequence_skips_job_for_duration_at_most_one_ms(monkeypatch):
    service = SchedulingService()
    sequence = Sequence(id="seq_schedule_guard", name="seq_schedule_guard")
    sequence.sequence_items = [
        _item("item_1", 1, _event("event_small", 1000, 0.001)),
        _item("item_2", 2, _event("event_valid", 2000, 1.0)),
    ]
    sequence_start = datetime(2026, 2, 28, 21, 0, 0, tzinfo=timezone.utc)
    scheduled_event_ids: list[str] = []

    monkeypatch.setattr(
        service,
        "_schedule_event",
        lambda _sequence_id, event_id, _event_name, _start_at, _duration_ms: scheduled_event_ids.append(event_id),
    )

    service._schedule_sequence(sequence, sequence_start)

    assert scheduled_event_ids == ["event_valid"]


def test_stop_sequence_stops_running_events_and_clears_pending_jobs(monkeypatch):
    service = SchedulingService()
    scheduler = _SchedulerStub()
    service._scheduler = scheduler
    published: list[tuple[str, str, str]] = []
    now = datetime(2026, 2, 28, 21, 0, 0, tzinfo=timezone.utc)

    monkeypatch.setattr(
        service,
        "_publish",
        lambda event_id, name, action: published.append((event_id, name, action)),
    )

    service._schedule_event("sequence_stop", "event_stop", "event_stop", now, 2000)
    start_job_id = scheduler.job_ids("start-")[0]
    stop_job_id = scheduler.job_ids("stop-")[0]
    service._run_start_job("sequence_stop", "event_stop", "event_stop", start_job_id)

    service.stop_sequence("sequence_stop")

    runtime = service.get_sequence_runtime("sequence_stop")
    assert runtime["is_running"] is False
    assert runtime["pending_start_jobs"] == 0
    assert runtime["pending_stop_jobs"] == 0
    assert stop_job_id in scheduler.removed_job_ids
    assert ("event_stop", "event_stop", "STOP") in published


def test_reset_execution_event_statuses_sets_all_to_off(app):
    service = SchedulingService()

    with app.app_context():
        event = ExecutionEvent(
            id="event_status_reset",
            name="event_status_reset",
            duration_ms=1000,
            activated=True,
            status=ExecutionEventStatus.ON,
        )
        db.session.add(event)
        db.session.commit()

        service.reset_execution_event_statuses()

        persisted = db.session.get(ExecutionEvent, "event_status_reset")
        assert persisted is not None
        assert persisted.status == ExecutionEventStatus.OFF


def _event(
    entity_id: str,
    duration_ms: int,
    factor_value: float,
    factor_activated: bool = True,
) -> ExecutionEvent:
    factor = Factor(
        id=f"factor_{entity_id}",
        name=f"factor_{entity_id}",
        factor=factor_value,
        activated=factor_activated,
    )
    event = ExecutionEvent(id=entity_id, name=entity_id, duration_ms=duration_ms, activated=True)
    event.factors = [factor]
    return event


def _item(item_id: str, order: int, event: ExecutionEvent) -> SequenceItem:
    item = SequenceItem(id=item_id, order=order)
    item.execution_event = event
    return item


def _persist_tick_trigger(
    target_time: datetime,
    recurrance_type: RecurranceType = RecurranceType.ONE_TIME,
    recurring: bool = True,
) -> None:
    event = ExecutionEvent(id="event_tick", name="event_tick", duration_ms=1000, activated=True)
    item = SequenceItem(id="item_tick", order=1)
    item.execution_event = event
    sequence = Sequence(id="sequence_tick", name="sequence_tick")
    sequence.sequence_items = [item]
    trigger_date = target_time.date() if recurrance_type != RecurranceType.WEEKLY else None
    trigger = Trigger(
        id="trigger_tick",
        name="trigger_tick",
        date=trigger_date,
        time=target_time.time(),
        activated=True,
        recurring=recurring,
        trigger_type=TriggerType.START_AT_POINT_IN_TIME,
        recurrance_type=recurrance_type,
    )
    trigger.sequences = [sequence]
    db.session.add_all([event, item, sequence, trigger])
    db.session.commit()


def _persist_trigger_with_multiple_sequences(target_time: datetime, durations_ms: list[int]) -> str:
    trigger = Trigger(
        id="trigger_multi_seq",
        name="trigger_multi_seq",
        date=target_time.date(),
        time=target_time.time(),
        activated=True,
        recurring=True,
        trigger_type=TriggerType.STOP_AT_POINT_IN_TIME,
        recurrance_type=RecurranceType.ONE_TIME,
    )

    sequences: list[Sequence] = []
    entities = [trigger]
    for index, duration_ms in enumerate(durations_ms, start=1):
        event = ExecutionEvent(
            id=f"event_multi_seq_{index}",
            name=f"event_multi_seq_{index}",
            duration_ms=duration_ms,
            activated=True,
        )
        item = SequenceItem(id=f"item_multi_seq_{index}", order=1)
        item.execution_event = event
        sequence = Sequence(id=f"sequence_multi_seq_{index}", name=f"sequence_multi_seq_{index}")
        sequence.sequence_items = [item]
        sequences.append(sequence)
        entities.extend([event, item, sequence])

    trigger.sequences = sequences
    db.session.add_all(entities)
    db.session.commit()
    return trigger.id


class _SchedulerStub:
    def __init__(self) -> None:
        self._jobs: set[str] = set()
        self.removed_job_ids: list[str] = []

    def add_job(self, _func, _trigger, run_date, args, id):
        _ = run_date, args
        self._jobs.add(id)

    def remove_job(self, job_id: str) -> None:
        if job_id not in self._jobs:
            raise KeyError(job_id)
        self._jobs.remove(job_id)
        self.removed_job_ids.append(job_id)

    def job_ids(self, prefix: str) -> list[str]:
        return [job_id for job_id in self._jobs if job_id.startswith(prefix)]
