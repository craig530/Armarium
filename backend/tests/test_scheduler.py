"""Tests for app.services.scheduler — APScheduler trigger anchoring."""
from datetime import datetime, timedelta
from types import SimpleNamespace

from app.services.scheduler import SchedulerService


def _job(**overrides):
    defaults = dict(
        id=1,
        job_type="auto_link",
        interval_hours=24,
        last_run_at=None,
        created_at=datetime(2026, 6, 16, 14, 13, 44),
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _is_grid_aligned(next_run_time, anchor, interval_hours):
    """True if next_run_time falls on the anchor + k*interval grid (for some
    whole k >= 1) — i.e. the trigger is anchored to a fixed timestamp rather
    than to "whenever _register() happened to run"."""
    delta = next_run_time.replace(tzinfo=None) - anchor
    interval = timedelta(hours=interval_hours)
    return delta >= interval and delta % interval == timedelta(0)


async def test_register_anchors_never_run_job_to_created_at():
    """A job that has never run (last_run_at is None) must anchor its first
    fire to the created_at grid, not to "registration time" + interval —
    otherwise every server restart resets the countdown and a job that never
    gets a full interval of uninterrupted uptime before the next restart can
    starve forever (this happened in production: jobs created days earlier
    had never fired because the host redeploys more often than the 24h
    interval)."""
    svc = SchedulerService()
    svc.scheduler.start()
    try:
        job = _job()
        svc._register(job)
        aps_job = svc.scheduler.get_job("sj_1")
        assert _is_grid_aligned(aps_job.next_run_time, job.created_at, job.interval_hours)
    finally:
        svc.scheduler.shutdown(wait=False)


async def test_register_anchors_previously_run_job_to_last_run_at():
    svc = SchedulerService()
    svc.scheduler.start()
    try:
        job = _job(last_run_at=datetime(2026, 6, 17, 9, 0, 0))
        svc._register(job)
        aps_job = svc.scheduler.get_job("sj_1")
        assert _is_grid_aligned(aps_job.next_run_time, job.last_run_at, job.interval_hours)
    finally:
        svc.scheduler.shutdown(wait=False)


async def test_register_is_idempotent_across_repeated_calls():
    """Re-registering the same never-run job (simulating repeated server
    restarts before it ever gets to fire) must not keep pushing next_run_time
    further into the future."""
    svc = SchedulerService()
    svc.scheduler.start()
    try:
        job = _job()
        svc._register(job)
        first = svc.scheduler.get_job("sj_1").next_run_time

        svc._register(job)
        second = svc.scheduler.get_job("sj_1").next_run_time

        assert first == second
    finally:
        svc.scheduler.shutdown(wait=False)
