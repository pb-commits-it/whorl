"""whorl FastAPI app — v0.1: photo in → JSON pest IDs out."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from whorl import __version__
from whorl.config import Settings, get_settings
from whorl.routes import health as health_routes
from whorl.routes import photos as photo_routes
from whorl.storage.photos import LocalDiskStore

_PKG = Path(__file__).parent
WEB_DIR = _PKG / "web"

_FALLBACK_INDEX = """<!doctype html>
<html><head><meta charset="utf-8"><title>whorl</title></head>
<body style="font-family:ui-monospace,monospace;background:#0a0e14;color:#c9d4e5;padding:32px">
<h1>whorl — backend running</h1>
<p>Frontend bundle not built yet. Run <code>cd web && npm install && npm run build</code>.</p>
<p>API:</p>
<ul>
  <li><a href="/api/health" style="color:#7dd3fc">/api/health</a></li>
  <li><code>POST /api/photos</code> (multipart: file, crop?, state?)</li>
</ul>
</body></html>
"""


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    settings.whorl_photo_dir.mkdir(parents=True, exist_ok=True)

    app = FastAPI(title="whorl", version=__version__)
    app.state.settings = settings
    app.state.photo_store = LocalDiskStore(settings.whorl_photo_dir)

    app.include_router(health_routes.router)
    app.include_router(photo_routes.router)

    assets_dir = WEB_DIR / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/")
    def index():
        index_path = WEB_DIR / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
        return HTMLResponse(_FALLBACK_INDEX)

    return app


app = create_app()
