"""WebSocket endpoint for live scan progress.

Frontend currently polls the REST endpoint; this is a placeholder so the route
table stays stable. Closes the socket immediately.
"""
from fastapi import APIRouter, WebSocket

router = APIRouter()


@router.websocket("/scans/{job_id}")
async def scan_progress_ws(websocket: WebSocket, job_id: str) -> None:
    await websocket.accept()
    await websocket.close()
