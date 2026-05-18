"""Schedule endpoints — get/update per-account scan schedule."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.models.schedule import Schedule
from backend.app.schemas.schedule import ScheduleRead, ScheduleUpdate
from backend.app.services.scheduler import reconcile_account_schedule

router = APIRouter()


@router.get("/{account_id}/schedule", response_model=ScheduleRead)
async def get_schedule(account_id: int, db: AsyncSession = Depends(get_db)) -> Schedule:
    stmt = select(Schedule).where(Schedule.account_id == account_id)
    result = await db.execute(stmt)
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not configured")
    return schedule


@router.put("/{account_id}/schedule", response_model=ScheduleRead)
async def update_schedule(
    account_id: int,
    payload: ScheduleUpdate,
    db: AsyncSession = Depends(get_db),
) -> Schedule:
    stmt = select(Schedule).where(Schedule.account_id == account_id)
    result = await db.execute(stmt)
    schedule = result.scalar_one_or_none()
    if not schedule:
        schedule = Schedule(account_id=account_id)
        db.add(schedule)
    schedule.mode = payload.mode
    schedule.daily_time = payload.daily_time
    schedule.interval_hours = payload.interval_hours
    schedule.enabled = payload.enabled
    await db.commit()
    await db.refresh(schedule)
    reconcile_account_schedule(schedule)
    return schedule
