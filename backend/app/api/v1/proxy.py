"""Image proxy for Instagram CDN avatars — avoids browser hotlink blocks."""
import re
from urllib.parse import unquote

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

router = APIRouter()

_ALLOWED_HOSTS = re.compile(
    r"^https://(?:[\w\-]+\.)?(?:cdninstagram\.com|fbcdn\.net|instagram\.com)/"
)

_HEADERS = {
    "User-Agent": "Instagram 219.0.0.12.117 Android",
    "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
}


@router.get("/proxy/avatar")
async def proxy_avatar(url: str) -> Response:
    """Fetch and return an Instagram CDN image, bypassing browser hotlink restrictions."""
    decoded = unquote(url)
    if not _ALLOWED_HOSTS.match(decoded):
        raise HTTPException(status_code=400, detail="URL not from an allowed Instagram CDN host")
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(decoded, headers=_HEADERS)
        content_type = resp.headers.get("content-type", "image/jpeg")
        return Response(
            content=resp.content,
            media_type=content_type,
            headers={"Cache-Control": "public, max-age=3600"},
        )
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="CDN request timed out") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
