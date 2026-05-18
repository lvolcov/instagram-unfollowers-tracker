"""Instagram login flow via Playwright + noVNC.

Endpoints:
- POST   /auth/login/start          → spawn Playwright session, return noVNC URL
- GET    /auth/login/status/{sid}   → poll login progress
- POST   /auth/login/cancel/{sid}   → cancel an in-progress login
"""
from fastapi import APIRouter, HTTPException

from backend.app.services.login_session import login_session_manager

router = APIRouter()


@router.post("/login/start")
async def start_login() -> dict:
    """Spawn a Playwright browser session for adding a new account."""
    session = await login_session_manager.start()
    return {
        "session_id": session.id,
        "novnc_url": f"/novnc/vnc.html?autoconnect=true&resize=remote&path=novnc/{session.id}",
        "expires_in": 600,
    }


@router.get("/login/status/{session_id}")
async def login_status(session_id: str) -> dict:
    session = login_session_manager.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Login session not found")
    return {
        "status": session.status,
        "account": session.account_summary,
        "error": session.error,
    }


@router.post("/login/cancel/{session_id}")
async def cancel_login(session_id: str) -> dict:
    await login_session_manager.cancel(session_id)
    return {"cancelled": True}
