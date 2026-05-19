"""Pydantic schemas for scan jobs."""
from typing import Literal

from pydantic import BaseModel

ScanStatus = Literal["queued", "running", "completed", "failed"]


class ScanProgress(BaseModel):
    phase: str
    current: int
    total: int


class ScanResult(BaseModel):
    snapshot_id: int
    new_unfollowers: int
    warning: str | None = None


class ScanJob(BaseModel):
    job_id: str
    tracked_account_id: int = 0
    status: ScanStatus
    progress: ScanProgress | None = None
    result: ScanResult | None = None
    error: str | None = None
