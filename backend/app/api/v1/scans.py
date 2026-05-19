"""Endpoints for triggering and monitoring scans of a tracked account."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.models.tracked_account import TrackedAccount
from backend.app.schemas.scan import ScanJob
from backend.app.services.scan_service import scan_service

router = APIRouter()


@router.post("/{tracked_id}/scan", response_model=ScanJob)
async def trigger_scan(
    tracked_id: int, db: AsyncSession = Depends(get_db)
) -> ScanJob:
    tracked = await db.get(TrackedAccount, tracked_id)
    if not tracked:
        raise HTTPException(status_code=404, detail="Tracked account not found")
    return await scan_service.enqueue(tracked_id)


@router.get("/{tracked_id}/scan/{job_id}", response_model=ScanJob)
async def get_scan(tracked_id: int, job_id: str) -> ScanJob:
    job = scan_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Scan job not found")
    return job
