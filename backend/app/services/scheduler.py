"""APScheduler integration — persistent per-account scan scheduling."""
from __future__ import annotations

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from backend.app.core.config import settings
from backend.app.models.schedule import Schedule


_scheduler: AsyncIOScheduler | None = None


def start_scheduler() -> None:
    global _scheduler
    # Use a sync SQLAlchemy URL for APScheduler's jobstore (it isn't async-aware).
    sync_url = f"sqlite:///{settings.DB_PATH}"
    jobstores = {"default": SQLAlchemyJobStore(url=sync_url)}
    _scheduler = AsyncIOScheduler(jobstores=jobstores, timezone=settings.TIMEZONE)
    _scheduler.start()


def shutdown_scheduler() -> None:
    if _scheduler:
        _scheduler.shutdown(wait=False)


def reconcile_account_schedule(schedule: Schedule) -> None:
    """Add/update/remove the APScheduler job for a given account schedule.

    TODO (Phase 4):
    - mode=daily_at: CronTrigger with hour/minute parsed from daily_time
    - mode=interval_hours: IntervalTrigger with given hours
    - mode=manual_only or enabled=False: remove existing job
    - job target: scan_service.enqueue(account_id)
    """
    if not _scheduler:
        return
    job_id = f"scan-tracked-{schedule.tracked_account_id}"
    # TODO: implementation
    _ = job_id
