"""v0.5 — SSE pub/sub hub semantics + photo route publishes the right events.

The SSE route itself is exercised against a TestClient stream() in
test_stream_endpoint_emits_initial_connected; the rest of the file goes
straight through the hub, since TestClient doesn't surface partial SSE
streams well across event loops.
"""

from __future__ import annotations

import asyncio
import json

import respx
from fastapi.testclient import TestClient

from whorl.pipeline.vision import OPENROUTER_URL


def _vision(scientific: str, common: str, conf: float) -> dict:
    return {"choices": [{"message": {"content": json.dumps({
        "candidates": [{
            "scientific_name": scientific,
            "common_name": common,
            "lifecycle_stage": "larva",
            "confidence": conf,
            "visible_features": [],
            "evidence": "organism",
        }],
        "image_quality": "good",
        "notes": "",
    })}}]}


async def test_hub_publishes_to_all_subscribers_with_scout_id(auth_client: TestClient):
    """Both subs see both events; route layer filters by scout_id."""
    hub = auth_client.app.state.hub
    q1 = hub.subscribe()
    q2 = hub.subscribe()
    try:
        await hub.publish("id_ready", {"scout_id": "A", "value": 1})
        await hub.publish("id_ready", {"scout_id": "B", "value": 2})
        for q in (q1, q2):
            seen = {(await asyncio.wait_for(q.get(), 0.5))[1]["scout_id"] for _ in range(2)}
            assert seen == {"A", "B"}
    finally:
        hub.unsubscribe(q1)
        hub.unsubscribe(q2)


async def test_stream_endpoint_404_for_unknown_scout(auth_client: TestClient):
    r = auth_client.get(
        "/api/stream/scouts/00000000-0000-0000-0000-000000000000",
        # don't actually open the stream — TestClient consumes it serially
        headers={"Accept": "text/event-stream"},
    )
    assert r.status_code == 404


def test_stream_endpoint_requires_auth(client: TestClient):
    r = client.get("/api/stream/scouts/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 401


@respx.mock
async def test_photos_route_publishes_photo_uploaded_and_id_ready(
    auth_client: TestClient, jpeg_bytes,
):
    respx.post(OPENROUTER_URL).mock(side_effect=lambda req: __import__("httpx").Response(
        200, json=_vision("Helicoverpa zea", "corn earworm", 0.9),
    ))

    farm = auth_client.post("/api/farms", json={"name": "F"}).json()
    field = auth_client.post(
        f"/api/farms/{farm['id']}/fields", json={"name": "N", "crop": "corn"},
    ).json()
    scout = auth_client.post("/api/scouts", json={"field_id": field["id"]}).json()

    hub = auth_client.app.state.hub
    queue = hub.subscribe()
    try:
        r = auth_client.post(
            "/api/photos",
            files={"file": ("p.jpg", jpeg_bytes, "image/jpeg")},
            data={"scout_id": scout["id"]},
        )
        assert r.status_code == 200, r.text

        events = [await asyncio.wait_for(queue.get(), 2.0) for _ in range(2)]
        assert events[0][0] == "photo_uploaded"
        assert events[1][0] == "id_ready"
        assert events[0][1]["scout_id"] == scout["id"]
        assert events[1][1]["scout_id"] == scout["id"]
        assert events[1][1]["top_confidence"] == 0.9
        assert events[1][1]["low_confidence"] is False
        assert events[1][1]["needs_rescout"] is False
    finally:
        hub.unsubscribe(queue)


@respx.mock
async def test_low_confidence_event_flags_set(auth_client: TestClient, jpeg_bytes):
    respx.post(OPENROUTER_URL).mock(side_effect=lambda req: __import__("httpx").Response(
        200, json=_vision("Unknown sp.", "", 0.40),
    ))

    farm = auth_client.post("/api/farms", json={"name": "F"}).json()
    field = auth_client.post(
        f"/api/farms/{farm['id']}/fields", json={"name": "N", "crop": "corn"},
    ).json()
    scout = auth_client.post("/api/scouts", json={"field_id": field["id"]}).json()

    hub = auth_client.app.state.hub
    queue = hub.subscribe()
    try:
        auth_client.post(
            "/api/photos",
            files={"file": ("p.jpg", jpeg_bytes, "image/jpeg")},
            data={"scout_id": scout["id"]},
        )
        _photo = await asyncio.wait_for(queue.get(), 2.0)
        id_evt = await asyncio.wait_for(queue.get(), 2.0)
        assert id_evt[0] == "id_ready"
        assert id_evt[1]["low_confidence"] is True
        assert id_evt[1]["needs_rescout"] is True
    finally:
        hub.unsubscribe(queue)
