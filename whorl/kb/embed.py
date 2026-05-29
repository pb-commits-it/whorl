"""Embeddings client — OpenRouter, defaults to openai/text-embedding-3-small."""

from __future__ import annotations

import logging

import httpx

EMBED_URL = "https://openrouter.ai/api/v1/embeddings"
DEFAULT_MODEL = "openai/text-embedding-3-small"

log = logging.getLogger("whorl.kb.embed")


async def embed_texts(
    texts: list[str],
    *,
    api_key: str,
    model: str = DEFAULT_MODEL,
    client: httpx.AsyncClient | None = None,
) -> list[list[float]]:
    """Embed a batch of texts via OpenRouter; returns one float vector per input."""
    if not texts:
        return []
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY not set; embeddings unavailable")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/pb-commits-it/whorl",
        "X-Title": "Whorl",
    }
    payload = {"model": model, "input": texts}

    own = client is None
    if own:
        client = httpx.AsyncClient(timeout=httpx.Timeout(60.0))
    try:
        resp = await client.post(EMBED_URL, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return [item["embedding"] for item in data["data"]]
    finally:
        if own:
            await client.aclose()
