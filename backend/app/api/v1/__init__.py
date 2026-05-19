"""Aggregate API v1 routers."""
from fastapi import APIRouter

from backend.app.api.v1 import (
    app_settings,
    auth,
    followers,
    health,
    login_account,
    proxy,
    scans,
    schedule,
    settings as settings_routes,
    tracked_accounts,
    unfollowers,
    webhook,
    whitelist,
    ws,
)

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(proxy.router, tags=["proxy"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(login_account.router, prefix="/login-account", tags=["login-account"])
api_router.include_router(
    tracked_accounts.router, prefix="/tracked-accounts", tags=["tracked-accounts"]
)
api_router.include_router(scans.router, prefix="/tracked-accounts", tags=["scans"])
api_router.include_router(followers.router, prefix="/tracked-accounts", tags=["followers"])
api_router.include_router(unfollowers.router, prefix="/tracked-accounts", tags=["unfollowers"])
api_router.include_router(whitelist.router, prefix="/tracked-accounts", tags=["whitelist"])
api_router.include_router(schedule.router, prefix="/schedules", tags=["schedules"])
api_router.include_router(settings_routes.router, prefix="/settings", tags=["settings"])
api_router.include_router(app_settings.router, prefix="/app-settings", tags=["app-settings"])
api_router.include_router(webhook.router, prefix="/webhook", tags=["webhook"])
api_router.include_router(ws.router, prefix="/ws", tags=["websocket"])
