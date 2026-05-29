"""Recommender — assembles context, calls the LLM with strict JSON, returns a `RecommendationResult`."""

from __future__ import annotations

import json
import logging
import time
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID

import httpx
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from whorl.kb.embed import embed_texts
from whorl.kb.rag import retrieve_wiki
from whorl.models import Application, Field, Identification, KBChunk, Photo, Scout
from whorl.pipeline.vision import OPENROUTER_URL
from whorl.schemas.recommend import RecommendationResult

if TYPE_CHECKING:
    from whorl.config import Settings

log = logging.getLogger("whorl.recommend")

PROMPT_VERSION = "v1.0"

SYSTEM_PROMPT = """\
You are a regional crop-scouting recommender for Midwest row crops, acting at
the experience level of an independent crop consultant or extension entomologist.
Given:
  (a) pest/disease identifications from one scouting session on one field,
  (b) the field's crop and state,
  (c) numbered excerpts from the regional pest/crop wiki — each with a [N] marker,
  (d) the field's RECENT APPLICATION HISTORY (last 5 sprays with MOA groups + dates),
produce ONE plain-English recommendation a farmer can act on today plus
structured fields.

Rules you MUST follow:
  1. Cite every numeric threshold, treatment claim, REI, or PHI using the
     [N] markers from the provided excerpts. The chunk_id in your citations
     output is the integer N from the brackets.
  2. If you recommend a CHEMICAL treatment, the recommended IRAC/FRAC/HRAC
     MOA group MUST DIFFER from the field's most recent same-pest MOA
     application (resistance management). Set chemical.rotation_rationale
     to explicitly reference the prior MOA + date.
  3. Always list at least one NON-CHEMICAL alternative (biological,
     cultural, or mechanical) when one exists in the provided excerpts.
  4. Respect REI / PHI from the cited product pages — surface REI hours
     and days-to-harvest in the chemical recommendation.
  5. If the excerpts do not support a confident recommendation, set
     action="scout_again" and describe what evidence is missing in
     plain_english.

Return STRICT JSON conforming to this schema and NOTHING ELSE — no markdown,
no code fences:
{
  "action": "no_action"|"monitor"|"scout_again"|"treat",
  "pest_focus": str,
  "threshold_context": str,
  "spray_window": null | {"open":"YYYY-MM-DD","close":"YYYY-MM-DD","reason":str},
  "chemical": null | {
      "product": str,
      "active_ingredient": str,
      "moa_class": "IRAC"|"FRAC"|"HRAC",
      "moa_group": str,
      "rotation_rationale": str,
      "rei_hours": int,
      "phi_days": int
  },
  "alternatives": [
      {"category": "biological"|"cultural"|"mechanical",
       "name": str,
       "summary": str,
       "kb_link": str}
  ],
  "plain_english": str,
  "confidence": "high"|"medium"|"low",
  "citations": [{"chunk_id": int, "quote": str}]
}
"""


def _build_context(
    field: Field,
    idents: list[Identification],
    chunks: list[KBChunk],
    recent_apps: list[Application],
) -> str:
    parts: list[str] = []
    parts.append(
        f"FIELD: {field.crop} in '{field.name}' "
        f"(planted {field.planting_date or 'unknown'}, variety {field.variety or 'unknown'})"
    )

    parts.append("\nIDENTIFICATIONS (this scout):")
    for i, ident in enumerate(idents[:5], 1):
        parts.append(
            f"  {i}. {ident.taxon_scientific} ({ident.taxon_common or '?'}) — "
            f"{ident.lifecycle_stage}, confidence {ident.confidence:.2f}"
        )

    parts.append("\nRECENT APPLICATIONS on this field (last 90 days):")
    if recent_apps:
        for app in recent_apps:
            parts.append(
                f"  · {app.applied_at.date()}: {app.product_name} "
                f"({app.active_ingredient or '?'}) — "
                f"{app.moa_class or '?'} group {app.moa_group or '?'}"
                + (f" targeting {app.pest_target}" if app.pest_target else "")
            )
    else:
        parts.append("  (none recorded)")

    parts.append("\nWIKI EXCERPTS — cite by [N]:")
    for n, c in enumerate(chunks, 1):
        parts.append(
            f"\n[{n}] (entity {c.entity_kind}/{c.entity_slug}; {c.citation})\n{c.text}"
        )

    return "\n".join(parts)


def _parse_strict(text: str) -> RecommendationResult:
    s = text.strip()
    if s.startswith("```"):
        lines = s.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        s = "\n".join(lines).strip()
    return RecommendationResult.model_validate_json(s)


async def _call_recommender(
    context: str, settings: "Settings"
) -> tuple[RecommendationResult, str]:
    if not settings.openrouter_api_key:
        raise RuntimeError("OPENROUTER_API_KEY not set")
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/pb-commits-it/whorl",
        "X-Title": "Whorl",
    }
    async with httpx.AsyncClient(timeout=httpx.Timeout(90.0)) as client:
        for model in (settings.openrouter_vision_model, settings.openrouter_fallback_model):
            for attempt in range(2):
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": context},
                    ],
                    "response_format": {"type": "json_object"},
                    "max_tokens": 1500,
                    "temperature": 0.2,
                }
                try:
                    resp = await client.post(OPENROUTER_URL, json=payload, headers=headers)
                    resp.raise_for_status()
                    content = resp.json()["choices"][0]["message"]["content"]
                    return _parse_strict(content), model
                except (json.JSONDecodeError, ValidationError, KeyError) as exc:
                    log.warning(
                        "recommender parse failed (model=%s attempt=%d): %s",
                        model, attempt + 1, exc,
                    )
                    continue
                except httpx.HTTPError as exc:
                    log.error("recommender request failed (model=%s): %s", model, exc)
                    break
    raise RuntimeError("recommender failed for both primary and fallback models")


async def generate_recommendation(
    session: AsyncSession,
    scout_id: UUID,
    settings: "Settings",
) -> tuple[RecommendationResult, str, int]:
    t0 = time.monotonic()

    scout = (await session.execute(select(Scout).where(Scout.id == scout_id))).scalar_one()
    field = (await session.execute(select(Field).where(Field.id == scout.field_id))).scalar_one()

    photos = (await session.execute(
        select(Photo).where(Photo.scout_id == scout_id)
    )).scalars().all()

    all_ids: list[Identification] = []
    for p in photos:
        ids = (await session.execute(
            select(Identification)
            .where(Identification.photo_id == p.id)
            .order_by(Identification.rank)
        )).scalars().all()
        all_ids.extend(ids)

    if not all_ids:
        raise ValueError(
            "scout has no identifications yet — upload at least one photo first"
        )

    top = all_ids[0]
    top_pest_slug = top.taxon_scientific.lower().replace(" ", "-")
    query_text = (
        f"{top.taxon_scientific} ({top.taxon_common or ''}) on {field.crop} "
        f"at {top.lifecycle_stage} stage — economic threshold, recommended "
        f"controls, MOA rotation"
    )
    embeddings = await embed_texts([query_text], api_key=settings.openrouter_api_key)
    q_emb = embeddings[0]

    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=90)
    recent_apps = (await session.execute(
        select(Application)
        .where(Application.field_id == field.id, Application.applied_at > cutoff)
        .order_by(Application.applied_at.desc())
        .limit(5)
    )).scalars().all()

    chunks = await retrieve_wiki(
        session,
        query_embedding=q_emb,
        crops=[field.crop],
        pests=[top_pest_slug],
        regions=["KS", "NE", "IA", "MO", "OK"],
        limit=8,
    )
    if not chunks:
        raise ValueError("knowledge base is empty — run `whorl kb ingest` first")

    context_text = _build_context(field, all_ids, chunks, recent_apps)
    result, model_used = await _call_recommender(context_text, settings)
    latency_ms = int((time.monotonic() - t0) * 1000)
    return result, model_used, latency_ms
