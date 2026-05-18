"""Health-check endpoint."""
import time

from fastapi import APIRouter

router = APIRouter()
_started_at = time.time()


@router.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "version": "0.1.0",
        "uptime_seconds": int(time.time() - _started_at),
    }
