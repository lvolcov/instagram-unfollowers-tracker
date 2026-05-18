"""WebSocket endpoint for live scan progress."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.app.services.scan_service import scan_service

router = APIRouter()


@router.websocket("/scans/{job_id}")
async def scan_progress_ws(websocket: WebSocket, job_id: str) -> None:
    await websocket.accept()
    try:
        async for event in scan_service.subscribe(job_id):
            await websocket.send_json(event)
    except WebSocketDisconnect:
        return
