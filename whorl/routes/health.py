"""GET /api/health — liveness + version + model used.

`/api/health` is the cheap "is uvicorn alive" probe used by Caddy and any
uptime monitor. `/api/health/deep` actually pings Postgres so we catch DB
outages instead of returning 200 while data writes silently fail.
"""

from __future__ import annotations

from fastapi import APIRouter, Request, Response
from sqlalchemy import text

from whorl import __version__

router = APIRouter()


@router.get("/api/health")
def health(request: Request) -> dict:
    return {
        "status": "ok",
        "version": __version__,
        "vision_model": request.app.state.settings.openrouter_vision_model,
        "fallback_model": request.app.state.settings.openrouter_fallback_model,
    }


@router.get("/api/health/deep")
async def health_deep(request: Request, response: Response) -> dict:
    """Deep check — verifies DB connectivity. Returns 503 if Postgres is down.

    Use this from external uptime checks; `/api/health` won't catch a DB
    outage because uvicorn keeps running and the basic route doesn't touch
    the engine.
    """
    factory = request.app.state.session_factory
    db_ok = False
    db_error: str | None = None
    try:
        async with factory() as session:
            res = await session.execute(text("SELECT 1"))
            db_ok = res.scalar() == 1
    except Exception as exc:   # noqa: BLE001
        db_error = f"{type(exc).__name__}: {exc}"

    if not db_ok:
        response.status_code = 503

    return {
        "status": "ok" if db_ok else "degraded",
        "version": __version__,
        "db": {"ok": db_ok, "error": db_error},
    }
