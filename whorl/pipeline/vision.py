"""Vision pass — Qwen3-VL via OpenRouter, structured-JSON output.

Returns a `VisionResult`. Falls back to `OPENROUTER_FALLBACK_MODEL` if the
primary model returns malformed JSON twice in a row.
"""

from __future__ import annotations

import base64
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
from pydantic import ValidationError

from whorl.schemas.photo import VisionResult

if TYPE_CHECKING:
    from whorl.config import Settings

log = logging.getLogger("whorl.vision")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

SYSTEM_PROMPT = """\
You are an entomology + crop pathology vision assistant. Given a single field
photograph, return up to 3 candidate identifications of the most likely
arthropod pest, weed, or disease shown. Use accepted scientific names. If the
photo shows only plant damage with no visible organism, identify the likely
causal pest from the damage pattern and set "evidence":"damage_only".

Return STRICT JSON conforming to this schema and NOTHING ELSE — no markdown,
no commentary, no code fences:
{
  "candidates": [
    {
      "scientific_name": str,
      "common_name": str,
      "lifecycle_stage": "egg"|"larva"|"nymph"|"adult"|"damage_only"|"disease"|"unknown",
      "confidence": float,
      "visible_features": [str, ...],
      "evidence": "organism"|"damage_only"
    }
  ],
  "image_quality": "good"|"marginal"|"poor",
  "notes": str
}
If image_quality is "poor", you may return an empty candidates array.
"""


def _image_data_url(path: str | Path, ext: str = "jpeg") -> str:
    data = Path(path).read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:image/{ext};base64,{b64}"


def _build_payload(
    model: str,
    image_data_url: str,
    *,
    crop: str | None,
    state: str | None,
    date_iso: str | None,
) -> dict:
    user_text = "Identify the pest / disease in this field photograph."
    parts: list[str] = []
    if crop:
        parts.append(f"Field crop: {crop}")
    if state:
        parts.append(f"Field location: {state}, USA")
    if date_iso:
        parts.append(f"Date: {date_iso}")
    if parts:
        user_text = "\n".join([user_text, *parts])

    return {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": [
                {"type": "text", "text": user_text},
                {"type": "image_url", "image_url": {"url": image_data_url}},
            ]},
        ],
        "response_format": {"type": "json_object"},
        "max_tokens": 800,
        "temperature": 0.2,
    }


def _parse_json_strict(text: str) -> VisionResult:
    """Parse JSON, tolerating accidental code fences from the model."""
    s = text.strip()
    if s.startswith("```"):
        lines = s.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        s = "\n".join(lines).strip()
    parsed = json.loads(s)
    return VisionResult.model_validate(parsed)


async def identify(
    photo_path: str | Path,
    settings: "Settings",
    *,
    crop: str | None = None,
    state: str | None = None,
    date_iso: str | None = None,
    client: httpx.AsyncClient | None = None,
) -> tuple[VisionResult, str]:
    """Identify pests / disease in a photo via OpenRouter.

    Returns (result, model_used). Raises if both primary and fallback fail.
    """
    if not settings.openrouter_api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set; copy .env.example to .env")

    image_url = _image_data_url(photo_path, ext="jpeg")
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/pb-commits-it/whorl",
        "X-Title": "Whorl",
    }

    own_client = client is None
    if own_client:
        client = httpx.AsyncClient(timeout=httpx.Timeout(60.0))
    try:
        for model in (settings.openrouter_vision_model, settings.openrouter_fallback_model):
            for attempt in range(2):
                payload = _build_payload(model, image_url, crop=crop, state=state, date_iso=date_iso)
                try:
                    resp = await client.post(OPENROUTER_URL, json=payload, headers=headers)
                    resp.raise_for_status()
                    content = resp.json()["choices"][0]["message"]["content"]
                    return _parse_json_strict(content), model
                except (json.JSONDecodeError, ValidationError, KeyError) as exc:
                    log.warning(
                        "vision parse failed (model=%s attempt=%d): %s",
                        model, attempt + 1, exc,
                    )
                    continue
                except httpx.HTTPError as exc:
                    log.error("vision request failed (model=%s): %s", model, exc)
                    break
        raise RuntimeError(
            f"Vision identify failed for both primary ({settings.openrouter_vision_model}) "
            f"and fallback ({settings.openrouter_fallback_model})."
        )
    finally:
        if own_client:
            await client.aclose()
