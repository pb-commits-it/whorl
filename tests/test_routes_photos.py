"""End-to-end: upload a photo to a scout → vision pass mocked → identifications persisted."""

from __future__ import annotations

import json

import httpx
import respx
from fastapi.testclient import TestClient

from whorl.pipeline.vision import OPENROUTER_URL


def _ok_vision_payload() -> dict:
    return {
        "choices": [{"message": {"content": json.dumps({
            "candidates": [{
                "scientific_name": "Helicoverpa zea",
                "common_name": "corn earworm",
                "lifecycle_stage": "larva",
                "confidence": 0.9,
                "visible_features": ["light-tan stripes"],
                "evidence": "organism",
            }],
            "image_quality": "good",
            "notes": "",
        })}}]
    }


def _setup_farm_field_scout(auth_client: TestClient) -> tuple[str, str, str]:
    farm = auth_client.post("/api/farms", json={"name": "Demo Farm"}).json()
    field = auth_client.post(
        f"/api/farms/{farm['id']}/fields", json={"name": "Field 1", "crop": "corn"}
    ).json()
    scout = auth_client.post("/api/scouts", json={"field_id": field["id"]}).json()
    return farm["id"], field["id"], scout["id"]


@respx.mock
def test_upload_photo_persists_identifications(auth_client: TestClient, jpeg_bytes):
    respx.post(OPENROUTER_URL).mock(
        return_value=httpx.Response(200, json=_ok_vision_payload())
    )
    farm_id, field_id, scout_id = _setup_farm_field_scout(auth_client)

    resp = auth_client.post(
        "/api/photos",
        files={"file": ("test.jpg", jpeg_bytes, "image/jpeg")},
        data={"scout_id": scout_id, "state": "KS"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["vision"]["candidates"][0]["scientific_name"] == "Helicoverpa zea"
    assert body["model_used"] == "test/primary"

    # Scout detail should now include the photo + identification.
    detail = auth_client.get(f"/api/scouts/{scout_id}").json()
    assert len(detail["photos"]) == 1
    ids = detail["photos"][0]["identifications"]
    assert len(ids) == 1
    assert ids[0]["taxon_scientific"] == "Helicoverpa zea"
    assert ids[0]["lifecycle_stage"] == "larva"
    assert ids[0]["confidence"] == 0.9


def test_upload_requires_auth(client: TestClient, jpeg_bytes):
    resp = client.post(
        "/api/photos",
        files={"file": ("test.jpg", jpeg_bytes, "image/jpeg")},
        data={"scout_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert resp.status_code == 401


def test_upload_rejects_unknown_scout(auth_client: TestClient, jpeg_bytes):
    resp = auth_client.post(
        "/api/photos",
        files={"file": ("test.jpg", jpeg_bytes, "image/jpeg")},
        data={"scout_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert resp.status_code == 404


def test_health_endpoint(client: TestClient):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["version"] == "0.3.0"
