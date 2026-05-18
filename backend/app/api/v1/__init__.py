"""Aggregate API v1 routers."""
from fastapi import APIRouter

from backend.app.api.v1 import (
    accounts,
    auth,
    followers,
    health,
    schedule,
    scans,
    settings as settings_routes,
    unfollowers,
    webhook,
    whitelist,
    ws,
)

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(accounts.router, prefix="/accounts", tags=["accounts"])
api_router.include_router(scans.router, prefix="/accounts", tags=["scans"])
api_router.include_router(followers.router, prefix="/accounts", tags=["followers"])
api_router.include_router(unfollowers.router, prefix="/accounts", tags=["unfollowers"])
api_router.include_router(whitelist.router, prefix="/accounts", tags=["whitelist"])
api_router.include_router(schedule.router, prefix="/accounts", tags=["schedule"])
api_router.include_router(settings_routes.router, prefix="/settings", tags=["settings"])
api_router.include_router(webhook.router, prefix="/webhook", tags=["webhook"])
api_router.include_router(ws.router, prefix="/ws", tags=["websocket"])
