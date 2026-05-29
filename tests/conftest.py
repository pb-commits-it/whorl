"""Shared test fixtures.

Tests use aiosqlite for the DB (fast, no external services) and respx to mock
the OpenRouter HTTP call. The real backing store at runtime is Postgres +
pgvector via docker-compose, but the same SQLAlchemy models work on both.
"""

from __future__ import annotations

import io
import re
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from whorl.app import create_app
from whorl.config import Settings


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Fresh `Settings` not loaded from the real `.env`, pointed at a tmp sqlite + tmp photo dir."""
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    s.openrouter_api_key = "test-key-not-real"
    s.openrouter_vision_model = "test/primary"
    s.openrouter_fallback_model = "test/fallback"
    s.whorl_photo_dir = tmp_path / "photos"
    s.database_url = f"sqlite+aiosqlite:///{tmp_path}/whorl.db"
    s.jwt_secret = "test-jwt-secret-32-chars-or-more-please"
    s.base_url = "http://testserver"
    return s


@pytest.fixture
def jpeg_bytes() -> bytes:
    """A valid tiny JPEG image (16x16, solid color)."""
    im = Image.new("RGB", (16, 16), (120, 200, 80))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=70)
    return buf.getvalue()


@pytest.fixture
def jpeg_file(tmp_path: Path, jpeg_bytes: bytes) -> Path:
    p = tmp_path / "test.jpg"
    p.write_bytes(jpeg_bytes)
    return p


@pytest.fixture
def client(settings) -> Iterator[TestClient]:
    """Unauthenticated `TestClient` with lifespan run (creates DB tables)."""
    app = create_app(settings)
    with TestClient(app) as c:
        yield c


def _follow_dev_link(client: TestClient, link: str) -> None:
    """Extract `token=...` from a dev magic link and follow /api/auth/verify."""
    m = re.search(r"token=([A-Za-z0-9_\-]+)", link)
    assert m, f"no token in {link}"
    resp = client.get(f"/api/auth/verify?token={m.group(1)}")
    assert resp.status_code == 200, resp.text


@pytest.fixture
def auth_client(client: TestClient) -> Iterator[TestClient]:
    """`TestClient` already signed up + signed in as a farmer org."""
    resp = client.post(
        "/api/auth/magic",
        json={"email": "scout@example.com", "org_type": "farmer", "name": "Test Scout"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["sent"] is True
    assert body["dev_link"]
    _follow_dev_link(client, body["dev_link"])
    yield client
