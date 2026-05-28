"""Shared test fixtures."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image

from whorl.config import Settings


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Fresh `Settings` not loaded from the real `.env`."""
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    s.openrouter_api_key = "test-key-not-real"
    s.openrouter_vision_model = "test/primary"
    s.openrouter_fallback_model = "test/fallback"
    s.whorl_photo_dir = tmp_path / "photos"
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
