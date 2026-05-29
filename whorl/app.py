"""whorl FastAPI app — v0.2: photo + auth + persistence."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine

from whorl import __version__
from whorl.config import Settings, get_settings
from whorl.db import init_db, make_engine, make_session_factory
from whorl.routes import auth as auth_routes
from whorl.routes import farms as farm_routes
from whorl.routes import health as health_routes
from whorl.routes import me as me_routes
from whorl.routes import photos as photo_routes
from whorl.routes import scouts as scout_routes
from whorl.storage.photos import LocalDiskStore

_PKG = Path(__file__).parent
WEB_DIR = _PKG / "web"

_FALLBACK_INDEX = """<!doctype html>
<html><head><meta charset="utf-8"><title>whorl</title></head>
<body style="font-family:ui-monospace,monospace;background:#0a0e14;color:#c9d4e5;padding:32px">
<h1>whorl — backend running</h1>
<p>Frontend bundle not built yet. Run <code>cd web &amp;&amp; npm install &amp;&amp; npm run build</code>.</p>
<p>API:</p>
<ul>
  <li><a href="/api/health" style="color:#7dd3fc">/api/health</a></li>
  <li><code>POST /api/auth/magic</code> · <code>GET /api/auth/verify?token=...</code></li>
  <li><code>GET /api/me</code></li>
  <li><code>GET|POST /api/farms</code> · <code>GET|POST /api/farms/:id/fields</code></li>
  <li><code>POST /api/scouts</code> · <code>GET /api/fields/:id/scouts</code> · <code>GET /api/scouts/:id</code></li>
  <li><code>POST /api/photos</code> (multipart: scout_id + file [+ crop, state])</li>
</ul>
</body></html>
"""


def _enable_sqlite_fk(engine: AsyncEngine) -> None:
    """SQLite needs FKs enabled per-connection. No-op on Postgres."""
    if not engine.url.get_backend_name().startswith("sqlite"):
        return

    @event.listens_for(engine.sync_engine, "connect")
    def _on_connect(dbapi_connection, _record):  # pragma: no cover
        cur = dbapi_connection.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    settings.whorl_photo_dir.mkdir(parents=True, exist_ok=True)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        engine = make_engine(settings.database_url)
        _enable_sqlite_fk(engine)
        session_factory = make_session_factory(engine)
        app.state.engine = engine
        app.state.session_factory = session_factory
        await init_db(engine)
        try:
            yield
        finally:
            await engine.dispose()

    app = FastAPI(title="whorl", version=__version__, lifespan=lifespan)
    app.state.settings = settings
    app.state.photo_store = LocalDiskStore(settings.whorl_photo_dir)

    app.include_router(health_routes.router)
    app.include_router(auth_routes.router)
    app.include_router(me_routes.router)
    app.include_router(farm_routes.router)
    app.include_router(scout_routes.router)
    app.include_router(photo_routes.router)

    assets_dir = WEB_DIR / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/")
    def index():
        idx = WEB_DIR / "index.html"
        if idx.exists():
            return FileResponse(idx)
        return HTMLResponse(_FALLBACK_INDEX)

    # SPA catch-all for client-side routes.
    @app.get("/login")
    @app.get("/app")
    @app.get("/app/{path:path}")
    def spa_route(path: str = ""):
        idx = WEB_DIR / "index.html"
        if idx.exists():
            return FileResponse(idx)
        return HTMLResponse(_FALLBACK_INDEX)

    return app


app = create_app()
