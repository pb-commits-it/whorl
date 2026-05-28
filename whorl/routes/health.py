"""GET /api/health — liveness + version + model used."""

from __future__ import annotations

from fastapi import APIRouter, Request

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
