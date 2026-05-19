"""Global schedules CRUD.

Many schedules per tracked account; each has its own frequency + optional
webhook URL override.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.models.schedule import Schedule
from backend.app.models.tracked_account import TrackedAccount
from backend.app.schemas.schedule import (
    ScheduleCreate,
    ScheduleRead,
    ScheduleUpdate,
)
from backend.app.services import scheduler as scheduler_svc

router = APIRouter()


@router.get("", response_model=list[ScheduleRead])
async def list_schedules(db: AsyncSession = Depends(get_db)) -> list[Schedule]:
    rows = (await db.execute(select(Schedule).order_by(Schedule.id))).scalars().all()
    return list(rows)


@router.post("", response_model=ScheduleRead)
async def create_schedule(
    payload: ScheduleCreate, db: AsyncSession = Depends(get_db)
) -> Schedule:
    tracked = await db.get(TrackedAccount, payload.tracked_account_id)
    if not tracked:
        raise HTTPException(status_code=404, detail="Tracked account not found")
    _validate(payload.mode, payload.daily_time, payload.weekly_day, payload.interval_hours)
    schedule = Schedule(
        tracked_account_id=payload.tracked_account_id,
        name=payload.name,
        mode=payload.mode,
        daily_time=payload.daily_time,
        weekly_day=payload.weekly_day,
        interval_hours=payload.interval_hours,
        webhook_url=payload.webhook_url,
        enabled=payload.enabled,
    )
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)
    scheduler_svc.reconcile(schedule)
    return schedule


@router.put("/{schedule_id}", response_model=ScheduleRead)
async def update_schedule(
    schedule_id: int,
    payload: ScheduleUpdate,
    db: AsyncSession = Depends(get_db),
) -> Schedule:
    schedule = await db.get(Schedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(schedule, field, value)
    _validate(
        schedule.mode, schedule.daily_time, schedule.weekly_day, schedule.interval_hours
    )
    await db.commit()
    await db.refresh(schedule)
    scheduler_svc.reconcile(schedule)
    return schedule


@router.delete("/{schedule_id}")
async def delete_schedule(
    schedule_id: int, db: AsyncSession = Depends(get_db)
) -> dict:
    schedule = await db.get(Schedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    scheduler_svc.remove(schedule_id)
    await db.delete(schedule)
    await db.commit()
    return {"deleted": True}


def _validate(
    mode: str | None,
    daily_time: str | None,
    weekly_day: int | None,
    interval_hours: int | None,
) -> None:
    if mode == "daily_at":
        if not daily_time or ":" not in daily_time:
            raise HTTPException(status_code=422, detail="daily_at requires daily_time HH:MM")
    elif mode == "weekly_on":
        if not daily_time or ":" not in daily_time:
            raise HTTPException(status_code=422, detail="weekly_on requires daily_time HH:MM")
        if weekly_day is None or not 0 <= weekly_day <= 6:
            raise HTTPException(status_code=422, detail="weekly_on requires weekly_day 0-6")
    elif mode == "interval_hours":
        if not interval_hours or interval_hours < 1:
            raise HTTPException(status_code=422, detail="interval_hours must be >= 1")
    else:
        raise HTTPException(status_code=422, detail=f"Unknown mode: {mode}")
