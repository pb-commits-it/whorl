"""Vision pass — structured JSON parsing + fallback model logic."""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from whorl.pipeline.vision import OPENROUTER_URL, identify
from whorl.schemas.photo import VisionResult


def _openrouter_response(content: str) -> dict:
    return {"choices": [{"message": {"content": content}}]}


GOOD_JSON = json.dumps({
    "candidates": [
        {
            "scientific_name": "Helicoverpa zea",
            "common_name": "corn earworm",
            "lifecycle_stage": "larva",
            "confidence": 0.86,
            "visible_features": ["light-tan stripes", "tan head capsule"],
            "evidence": "organism",
        }
    ],
    "image_quality": "good",
    "notes": "single L3 larva on corn silk",
})


@respx.mock
async def test_vision_parses_good_json(settings, jpeg_file):
    route = respx.post(OPENROUTER_URL).mock(
        return_value=httpx.Response(200, json=_openrouter_response(GOOD_JSON))
    )

    result, model = await identify(jpeg_file, settings, crop="corn", state="KS")

    assert route.called
    assert isinstance(result, VisionResult)
    assert len(result.candidates) == 1
    assert result.candidates[0].scientific_name == "Helicoverpa zea"
    assert result.candidates[0].confidence == pytest.approx(0.86)
    assert result.image_quality == "good"
    assert model == settings.openrouter_vision_model


@respx.mock
async def test_vision_strips_code_fences(settings, jpeg_file):
    fenced = "```json\n" + GOOD_JSON + "\n```"
    respx.post(OPENROUTER_URL).mock(
        return_value=httpx.Response(200, json=_openrouter_response(fenced))
    )

    result, model = await identify(jpeg_file, settings)

    assert len(result.candidates) == 1
    assert model == settings.openrouter_vision_model


@respx.mock
async def test_vision_falls_back_on_malformed_json(settings, jpeg_file):
    """Primary returns garbage twice, fallback returns good JSON — fallback model is used."""

    def respond(request):
        body = json.loads(request.content)
        if body["model"] == settings.openrouter_vision_model:
            return httpx.Response(200, json=_openrouter_response("definitely not json {"))
        return httpx.Response(200, json=_openrouter_response(GOOD_JSON))

    respx.post(OPENROUTER_URL).mock(side_effect=respond)

    result, model = await identify(jpeg_file, settings)

    assert len(result.candidates) == 1
    assert model == settings.openrouter_fallback_model


@respx.mock
async def test_vision_raises_when_both_fail(settings, jpeg_file):
    respx.post(OPENROUTER_URL).mock(
        return_value=httpx.Response(200, json=_openrouter_response("nope, not json"))
    )

    with pytest.raises(RuntimeError, match="failed"):
        await identify(jpeg_file, settings)


async def test_vision_raises_without_api_key(jpeg_file, tmp_path):
    from whorl.config import Settings

    s = Settings(_env_file=None)  # type: ignore[call-arg]
    s.openrouter_api_key = ""
    s.whorl_photo_dir = tmp_path / "photos"

    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
        await identify(jpeg_file, s)
