"""Pydantic schemas for scan jobs."""
from typing import Literal

from pydantic import BaseModel

ScanStatus = Literal["queued", "running", "completed", "failed"]


class ScanProgress(BaseModel):
    phase: Literal["followers", "following", "diff", "notify"]
    current: int
    total: int


class ScanResult(BaseModel):
    snapshot_id: int
    new_unfollowers: int


class ScanJob(BaseModel):
    job_id: str
    status: ScanStatus
    progress: ScanProgress | None = None
    result: ScanResult | None = None
    error: str | None = None
