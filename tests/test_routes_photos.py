"""Integration test for POST /api/photos and /api/health."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import respx
from fastapi.testclient import TestClient

from whorl.app import create_app
from whorl.pipeline.vision import OPENROUTER_URL


def _ok_vision_payload() -> dict:
    return {
        "choices": [{"message": {"content": json.dumps({
            "candidates": [{
                "scientific_name": "Helicoverpa zea",
                "common_name": "corn earworm",
                "lifecycle_stage": "larva",
                "confidence": 0.9,
                "visible_features": [],
                "evidence": "organism",
            }],
            "image_quality": "good",
            "notes": "",
        })}}]
    }


@respx.mock
def test_upload_photo_returns_vision_candidates(settings, jpeg_bytes):
    respx.post(OPENROUTER_URL).mock(
        return_value=httpx.Response(200, json=_ok_vision_payload())
    )

    app = create_app(settings)
    client = TestClient(app)

    resp = client.post(
        "/api/photos",
        files={"file": ("test.jpg", jpeg_bytes, "image/jpeg")},
        data={"crop": "corn", "state": "KS"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["vision"]["candidates"][0]["scientific_name"] == "Helicoverpa zea"
    assert body["model_used"] == settings.openrouter_vision_model
    assert body["width"] == 16 and body["height"] == 16
    assert body["sha256"]
    assert Path(body["stored_path"]).exists()
    assert Path(body["thumb_path"]).exists()


def test_upload_rejects_empty_file(settings):
    app = create_app(settings)
    client = TestClient(app)
    resp = client.post(
        "/api/photos",
        files={"file": ("test.jpg", b"", "image/jpeg")},
    )
    assert resp.status_code == 400


def test_health_endpoint(settings):
    app = create_app(settings)
    client = TestClient(app)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["vision_model"] == settings.openrouter_vision_model
    assert body["fallback_model"] == settings.openrouter_fallback_model
