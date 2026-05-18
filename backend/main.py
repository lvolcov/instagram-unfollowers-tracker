"""FastAPI entrypoint for Instagram Unfollowers Tracker."""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.app.api.v1 import api_router
from backend.app.core.config import settings
from backend.app.core.database import init_db
from backend.app.services.scheduler import start_scheduler, shutdown_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    start_scheduler()
    yield
    # Shutdown
    shutdown_scheduler()


app = FastAPI(
    title="Instagram Unfollowers Tracker",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# CORS — same-origin in production, permissive in dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount versioned API
app.include_router(api_router, prefix="/api/v1")


# ----- Static frontend -----
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend_dist"

if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # SPA fallback — let React Router handle client-side routes.
        # Don't intercept API or websocket routes.
        if full_path.startswith(("api/", "ws/", "novnc/")):
            return {"detail": "Not found"}, 404
        index_file = FRONTEND_DIST / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"detail": "Frontend not built"}, 503
