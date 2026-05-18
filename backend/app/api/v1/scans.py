"""Endpoints for triggering and monitoring scans."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.schemas.scan import ScanJob
from backend.app.services.scan_service import scan_service

router = APIRouter()


@router.post("/{account_id}/scan", response_model=ScanJob)
async def trigger_scan(account_id: int, db: AsyncSession = Depends(get_db)) -> ScanJob:
    """Enqueue an immediate scan for the given account."""
    job = await scan_service.enqueue(account_id)
    return job


@router.get("/{account_id}/scan/{job_id}", response_model=ScanJob)
async def get_scan(account_id: int, job_id: str) -> ScanJob:
    job = scan_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Scan job not found")
    return job


@router.get("/{account_id}/snapshots")
async def list_snapshots(
    account_id: int,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
) -> dict:
    # TODO: implement listing
    return {"snapshots": [], "page": page, "page_size": page_size}
