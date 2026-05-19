"""APScheduler integration — actual cron / interval scheduling.

Each `Schedule` row maps to one APScheduler job. `reconcile(schedule)` is
called whenever a schedule is created, updated, deleted or its enabled flag
flipped; it adds/replaces/removes the corresponding job in-place.

Triggers:
- mode="daily_at"      → CronTrigger(hour, minute) from `daily_time`
- mode="weekly_on"     → CronTrigger(day_of_week, hour, minute) using `weekly_day`
- mode="interval_hours"→ IntervalTrigger(hours=interval_hours)
- enabled=False        → job removed

The job target is `_run_scan(schedule_id, tracked_account_id)`, which enqueues
a scan and records last_run_at / last_run_status on the schedule row.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import structlog
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select

from backend.app.core.config import settings
from backend.app.core.database import AsyncSessionLocal
from backend.app.models.schedule import Schedule

logger = structlog.get_logger(__name__)

_scheduler: AsyncIOScheduler | None = None


def start_scheduler() -> None:
    global _scheduler
    sync_url = f"sqlite:///{settings.DB_PATH}"
    jobstores = {"default": SQLAlchemyJobStore(url=sync_url)}
    _scheduler = AsyncIOScheduler(jobstores=jobstores, timezone=settings.TIMEZONE)
    _scheduler.start()
    logger.info("scheduler.started", timezone=settings.TIMEZONE)
    # Reconcile all schedules from the DB on startup so jobs survive restarts.
    asyncio.create_task(_reconcile_all_on_startup())


def shutdown_scheduler() -> None:
    if _scheduler:
        _scheduler.shutdown(wait=False)
        logger.info("scheduler.shutdown")


def _job_id(schedule_id: int) -> str:
    return f"scan-schedule-{schedule_id}"


def _build_trigger(schedule: Schedule):
    if schedule.mode == "daily_at" and schedule.daily_time:
        hour, minute = (int(x) for x in schedule.daily_time.split(":", 1))
        return CronTrigger(hour=hour, minute=minute, timezone=settings.TIMEZONE)
    if schedule.mode == "weekly_on" and schedule.daily_time and schedule.weekly_day is not None:
        hour, minute = (int(x) for x in schedule.daily_time.split(":", 1))
        # APScheduler day_of_week: 0=mon..6=sun, matching our convention.
        return CronTrigger(
            day_of_week=schedule.weekly_day,
            hour=hour,
            minute=minute,
            timezone=settings.TIMEZONE,
        )
    if schedule.mode == "interval_hours" and schedule.interval_hours:
        return IntervalTrigger(hours=schedule.interval_hours, timezone=settings.TIMEZONE)
    return None


def reconcile(schedule: Schedule) -> None:
    """Add/replace/remove the APScheduler job for a single schedule row."""
    if not _scheduler:
        return
    job_id = _job_id(schedule.id)

    if not schedule.enabled:
        try:
            _scheduler.remove_job(job_id)
            logger.info("scheduler.removed", schedule_id=schedule.id)
        except Exception:
            pass
        return

    trigger = _build_trigger(schedule)
    if trigger is None:
        try:
            _scheduler.remove_job(job_id)
        except Exception:
            pass
        logger.warning("scheduler.invalid_config", schedule_id=schedule.id, mode=schedule.mode)
        return

    _scheduler.add_job(
        _run_scan,
        trigger=trigger,
        args=[schedule.id, schedule.tracked_account_id],
        id=job_id,
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300,
    )
    job = _scheduler.get_job(job_id)
    next_run = job.next_run_time if job else None
    logger.info(
        "scheduler.reconciled",
        schedule_id=schedule.id,
        mode=schedule.mode,
        next_run=str(next_run) if next_run else None,
    )

    # Persist next_run_at so the UI can show it.
    asyncio.create_task(_store_next_run(schedule.id, next_run))


def remove(schedule_id: int) -> None:
    if not _scheduler:
        return
    try:
        _scheduler.remove_job(_job_id(schedule_id))
        logger.info("scheduler.removed", schedule_id=schedule_id)
    except Exception:
        pass


async def _store_next_run(schedule_id: int, next_run) -> None:
    async with AsyncSessionLocal() as db:
        s = await db.get(Schedule, schedule_id)
        if s:
            s.next_run_at = next_run.replace(tzinfo=None) if next_run else None
            await db.commit()


async def _reconcile_all_on_startup() -> None:
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(Schedule))).scalars().all()
    for s in rows:
        reconcile(s)
    logger.info("scheduler.bootstrapped", schedules=len(rows))


async def _run_scan(schedule_id: int, tracked_account_id: int) -> None:
    """APScheduler entrypoint — enqueue a scan and record outcome on the row."""
    # Imported lazily to avoid a circular import (scan_service → webhook_service
    # → settings, all already imported by the time the scheduler fires).
    from backend.app.services.scan_service import scan_service

    log = logger.bind(schedule_id=schedule_id, tracked_account_id=tracked_account_id)
    log.info("schedule.firing")
    job = await scan_service.enqueue(
        tracked_account_id, schedule_id=schedule_id
    )
    # Reflect "queued" on the schedule row immediately; scan_service will
    # update last_run_status to "completed" / "failed" on its own.
    async with AsyncSessionLocal() as db:
        s = await db.get(Schedule, schedule_id)
        if s:
            s.last_run_at = datetime.now(timezone.utc)
            s.last_run_status = "queued"
            await db.commit()
    log.info("schedule.enqueued", job_id=job.job_id)
