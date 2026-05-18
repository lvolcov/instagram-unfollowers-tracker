"""FastAPI entrypoint for Instagram Unfollowers Tracker."""
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from backend.app.api.v1 import api_router
from backend.app.core.config import settings
from backend.app.core.database import init_db
from backend.app.services.scheduler import start_scheduler, shutdown_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(
    title="Instagram Unfollowers Tracker",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


# ----- noVNC proxy -----
# websockify runs on internal port 6080 and proxies WebSocket → VNC (port 5900).
# We serve the noVNC static files directly and proxy WebSocket connections.
NOVNC_STATIC = Path("/usr/share/novnc")


@app.websocket("/novnc/{path:path}")
async def novnc_ws_proxy(websocket: WebSocket, path: str):
    """Proxy WebSocket VNC connections from the browser to the local websockify server."""
    import websockets  # installed via uvicorn[standard]

    subprotocol = websocket.headers.get("sec-websocket-protocol", "")
    accepted = next(
        (p.strip() for p in subprotocol.split(",") if p.strip() in ("binary", "base64")),
        None,
    )
    await websocket.accept(subprotocol=accepted)

    ws_kwargs: dict = {}
    if accepted:
        ws_kwargs["subprotocols"] = [accepted]

    try:
        async with websockets.connect("ws://localhost:6080", **ws_kwargs) as vnc:

            async def client_to_vnc() -> None:
                try:
                    async for chunk in websocket.iter_bytes():
                        await vnc.send(chunk)
                except Exception:
                    pass

            async def vnc_to_client() -> None:
                try:
                    async for msg in vnc:
                        if isinstance(msg, bytes):
                            await websocket.send_bytes(msg)
                        else:
                            await websocket.send_text(msg)
                except Exception:
                    pass

            tasks = [
                asyncio.create_task(client_to_vnc()),
                asyncio.create_task(vnc_to_client()),
            ]
            _, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for t in pending:
                t.cancel()
    except Exception:
        pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


if NOVNC_STATIC.exists():
    app.mount("/novnc", StaticFiles(directory=NOVNC_STATIC, html=True), name="novnc")


# ----- React SPA -----
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend_dist"

if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith(("api/", "ws/")):
            return JSONResponse({"detail": "Not found"}, status_code=404)
        index_file = FRONTEND_DIST / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return JSONResponse({"detail": "Frontend not built"}, status_code=503)
