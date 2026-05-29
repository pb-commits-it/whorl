"""Retrieval — wiki-first cosine sim with tag boosts.

Python-side cosine over a small in-memory wiki (~30 chunks at launch). Swaps
to pgvector + HNSW around 1k chunks when raw-source ingest lands.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from whorl.models import KBChunk


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


async def retrieve_wiki(
    session: AsyncSession,
    *,
    query_embedding: list[float],
    crops: list[str] | None = None,
    pests: list[str] | None = None,
    regions: list[str] | None = None,
    limit: int = 8,
) -> list[KBChunk]:
    """Top-k wiki chunks by cosine + small tag-match boosts."""
    rows = (await session.execute(
        select(KBChunk).where(KBChunk.chunk_type == "wiki")
    )).scalars().all()

    crops = [c.lower() for c in (crops or [])]
    pests = [p.lower() for p in (pests or [])]
    regions = [r.upper() for r in (regions or [])]

    scored: list[tuple[float, KBChunk]] = []
    for c in rows:
        sim = cosine(query_embedding, c.embedding or [])
        boost = 0.0
        if crops and any(x in (c.crops or []) for x in crops):
            boost += 0.08
        if pests and any(x in [p.lower() for p in (c.pests or [])] for x in pests):
            boost += 0.12      # pest match is the most important signal
        if regions and any(x in [r.upper() for r in (c.regions or [])] for x in regions):
            boost += 0.05
        scored.append((sim + boost, c))

    scored.sort(reverse=True, key=lambda t: t[0])
    return [c for _, c in scored[:limit]]
