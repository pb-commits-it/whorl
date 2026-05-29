"""Recommender end-to-end with mocked OpenRouter (vision + embeddings + recommend)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import httpx
import respx
from fastapi.testclient import TestClient

from whorl.kb.embed import EMBED_URL
from whorl.kb.ingest import ingest_wiki
from whorl.pipeline.vision import OPENROUTER_URL


def _ok_vision(scientific: str = "Helicoverpa zea", common: str = "corn earworm") -> dict:
    return {
        "choices": [{"message": {"content": json.dumps({
            "candidates": [{
                "scientific_name": scientific,
                "common_name": common,
                "lifecycle_stage": "larva",
                "confidence": 0.9,
                "visible_features": [],
                "evidence": "organism",
            }],
            "image_quality": "good",
            "notes": "",
        })}}]
    }


def _ok_recommendation() -> dict:
    payload = {
        "action": "treat",
        "pest_focus": "Helicoverpa zea",
        "threshold_context": "Above 1 larva/ear at silking [1].",
        "spray_window": {
            "open": "2026-06-04", "close": "2026-06-06",
            "reason": "winds below 10 mph through Friday noon",
        },
        "chemical": {
            "product": "Conserve SC",
            "active_ingredient": "spinosad",
            "moa_class": "IRAC",
            "moa_group": "5",
            "rotation_rationale": "Field had IRAC 3A bifenthrin 14 days ago; rotate off pyrethroids.",
            "rei_hours": 4,
            "phi_days": 1,
        },
        "alternatives": [{
            "category": "biological",
            "name": "Bacillus thuringiensis var. kurstaki",
            "summary": "Selective; effective on L1-L2 larvae; apply evening.",
            "kb_link": "alt-controls/biological/bt-kurstaki",
        }],
        "plain_english": "Treat with Conserve SC (spinosad, IRAC 5). Avoid IRAC 3A — used 14 days ago.",
        "confidence": "high",
        "citations": [{"chunk_id": 1, "quote": "threshold 1 larva/ear"}],
    }
    return {"choices": [{"message": {"content": json.dumps(payload)}}]}


def _embedding_response(n: int, dim: int = 8) -> dict:
    return {"data": [{"embedding": [0.1 + i * 0.01] * dim, "index": i} for i in range(n)]}


def _route_openrouter_for_recommend(request: httpx.Request) -> httpx.Response:
    """Vision calls have an image_url in user content; recommendation is text only."""
    body = json.loads(request.content)
    user_msg = body["messages"][-1]["content"]
    if isinstance(user_msg, list):
        # Multimodal payload — vision call
        return httpx.Response(200, json=_ok_vision())
    # Text-only — recommendation call
    return httpx.Response(200, json=_ok_recommendation())


def _route_embeddings(request: httpx.Request) -> httpx.Response:
    body = json.loads(request.content)
    n = len(body["input"]) if isinstance(body["input"], list) else 1
    return httpx.Response(200, json=_embedding_response(n))


@respx.mock
async def test_full_recommend_flow(auth_client: TestClient, jpeg_bytes):
    """Sign up → farm → field → app history (IRAC 3A) → scout + photo → recommend."""
    respx.post(OPENROUTER_URL).mock(side_effect=_route_openrouter_for_recommend)
    respx.post(EMBED_URL).mock(side_effect=_route_embeddings)

    # 1. Pre-ingest the wiki (uses mocked embeddings).
    app = auth_client.app
    factory = app.state.session_factory
    async with factory() as session:
        await ingest_wiki(session, api_key="not-used-by-mock")

    # 2. Create farm + field.
    farm = auth_client.post("/api/farms", json={"name": "Demo"}).json()
    field = auth_client.post(
        f"/api/farms/{farm['id']}/fields", json={"name": "F1", "crop": "corn"},
    ).json()

    # 3. Log a recent IRAC 3A application.
    when = (datetime.now(tz=timezone.utc) - timedelta(days=14)).isoformat()
    r = auth_client.post("/api/applications", json={
        "field_id": field["id"], "applied_at": when,
        "product_name": "Brigade 2EC", "active_ingredient": "bifenthrin",
        "moa_class": "IRAC", "moa_group": "3A",
        "pest_target": "Helicoverpa zea",
    })
    assert r.status_code == 201, r.text

    # 4. Start scout, upload photo (vision call mocked → produces an Identification).
    scout = auth_client.post("/api/scouts", json={"field_id": field["id"]}).json()
    r = auth_client.post(
        "/api/photos",
        files={"file": ("test.jpg", jpeg_bytes, "image/jpeg")},
        data={"scout_id": scout["id"]},
    )
    assert r.status_code == 200, r.text

    # 5. Generate recommendation.
    r = auth_client.post(f"/api/scouts/{scout['id']}/recommend")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["result"]["action"] == "treat"
    assert body["result"]["chemical"]["moa_group"] == "5"   # rotation off 3A
    assert "3A" in body["result"]["chemical"]["rotation_rationale"]
    assert any(a["category"] == "biological" for a in body["result"]["alternatives"])
    assert body["result"]["chemical"]["rei_hours"] == 4
    assert body["result"]["chemical"]["phi_days"] == 1

    # 6. GET the recommendation back from a separate endpoint.
    r = auth_client.get(f"/api/scouts/{scout['id']}/recommendation")
    assert r.status_code == 200
    assert r.json()["result"]["pest_focus"] == "Helicoverpa zea"


@respx.mock
async def test_low_confidence_triggers_scout_again(auth_client: TestClient, jpeg_bytes):
    """v0.5 — top ID < 0.55 confidence → deterministic scout_again, no LLM call."""
    low_conf_vision = {
        "choices": [{"message": {"content": json.dumps({
            "candidates": [{
                "scientific_name": "Unknown sp.",
                "common_name": "",
                "lifecycle_stage": "unknown",
                "confidence": 0.40,
                "visible_features": [],
                "evidence": "damage_only",
            }],
            "image_quality": "marginal",
            "notes": "",
        })}}]
    }

    # Vision returns low-confidence; embedding + recommend should NOT be called.
    embed_route = respx.post(EMBED_URL).mock(return_value=httpx.Response(200, json=_embedding_response(1)))

    def _route(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        user_msg = body["messages"][-1]["content"]
        if isinstance(user_msg, list):
            return httpx.Response(200, json=low_conf_vision)
        # Recommendation text call should never fire on this path.
        raise AssertionError("low-confidence path should not call the LLM recommender")
    respx.post(OPENROUTER_URL).mock(side_effect=_route)

    farm = auth_client.post("/api/farms", json={"name": "Demo"}).json()
    field = auth_client.post(
        f"/api/farms/{farm['id']}/fields", json={"name": "F1", "crop": "corn"},
    ).json()
    scout = auth_client.post("/api/scouts", json={"field_id": field["id"]}).json()
    r = auth_client.post(
        "/api/photos",
        files={"file": ("p.jpg", jpeg_bytes, "image/jpeg")},
        data={"scout_id": scout["id"]},
    )
    assert r.status_code == 200, r.text

    r = auth_client.post(f"/api/scouts/{scout['id']}/recommend")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["result"]["action"] == "scout_again"
    assert body["result"]["confidence"] == "low"
    assert "55" in body["result"]["threshold_context"] or "0.55" in body["result"]["threshold_context"]
    assert body["model_used"] == "rescout-fallback"
    assert not embed_route.called, "embeddings should not be called on the scout_again shortcut"


@respx.mock
async def test_recommend_requires_at_least_one_identification(
    auth_client: TestClient,
):
    respx.post(OPENROUTER_URL).mock(return_value=httpx.Response(200, json=_ok_recommendation()))

    farm = auth_client.post("/api/farms", json={"name": "Demo"}).json()
    field = auth_client.post(
        f"/api/farms/{farm['id']}/fields", json={"name": "F1", "crop": "corn"},
    ).json()
    scout = auth_client.post("/api/scouts", json={"field_id": field["id"]}).json()

    # No photo uploaded yet → no identifications → 400.
    r = auth_client.post(f"/api/scouts/{scout['id']}/recommend")
    assert r.status_code == 400
    assert "identifications" in r.json()["detail"]
