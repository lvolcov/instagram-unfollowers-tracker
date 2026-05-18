"""Scan orchestration: enqueue, run, track progress, fan out events."""
from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator
from datetime import datetime

from backend.app.schemas.scan import ScanJob, ScanProgress, ScanResult


class ScanService:
    """Coordinates manual and scheduled scans.

    TODO (Phase 1):
    - Implement enqueue: insert snapshot row, kick off async worker
    - Worker calls InstagramClient.fetch_followers/following
    - Persist SnapshotUser rows in bulk
    - Diff against previous snapshot, insert Unfollower rows
    - Fire HA webhook on new unfollowers
    - Stream progress events to WS subscribers
    """

    def __init__(self) -> None:
        self._jobs: dict[str, ScanJob] = {}
        self._subscribers: dict[str, list[asyncio.Queue]] = {}

    async def enqueue(self, account_id: int) -> ScanJob:
        job_id = uuid.uuid4().hex
        job = ScanJob(job_id=job_id, status="queued")
        self._jobs[job_id] = job
        # TODO: spawn worker task
        return job

    def get_job(self, job_id: str) -> ScanJob | None:
        return self._jobs.get(job_id)

    async def subscribe(self, job_id: str) -> AsyncIterator[dict]:
        """WebSocket subscription for live progress events."""
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.setdefault(job_id, []).append(queue)
        try:
            while True:
                event = await queue.get()
                yield event
                if event.get("type") in {"complete", "error"}:
                    break
        finally:
            self._subscribers.get(job_id, []).remove(queue)

    async def _emit(self, job_id: str, event: dict) -> None:
        for queue in self._subscribers.get(job_id, []):
            await queue.put(event)


scan_service = ScanService()
