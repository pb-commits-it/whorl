"""Wiki ingest end-to-end with mocked embeddings — verifies DB rows + tags."""

from __future__ import annotations

import pytest
from sqlalchemy import func, select

from whorl.kb.ingest import ingest_wiki
from whorl.models import KBChunk, KBSource


@pytest.fixture
def patch_embed(monkeypatch):
    """Replace embed_texts with a deterministic stub so we don't hit OpenRouter."""
    async def fake_embed(texts, *, api_key, model="x"):
        # Return one (dim=8) vector per text — values seeded by text hash so each
        # chunk gets a distinct embedding.
        out = []
        for t in texts:
            h = abs(hash(t))
            v = [((h >> (i * 4)) & 0xF) / 15.0 for i in range(8)]
            out.append(v)
        return out

    monkeypatch.setattr("whorl.kb.ingest.embed_texts", fake_embed)


async def test_ingest_populates_sources_and_chunks(client, patch_embed):
    """Server's lifespan already ran init_db; we drive ingest via the session factory."""
    app = client.app
    factory = app.state.session_factory

    async with factory() as session:
        stats = await ingest_wiki(session, api_key="not-used-by-fake")

    assert stats["pages"] >= 10
    assert stats["chunks"] >= stats["pages"]   # at least one chunk per page

    async with factory() as session:
        sources = (await session.execute(select(KBSource))).scalars().all()
        chunks = (await session.execute(select(KBChunk))).scalars().all()
        helico_chunks = (await session.execute(
            select(KBChunk).where(KBChunk.entity_slug == "helicoverpa-zea")
        )).scalars().all()
        n = (await session.execute(select(func.count()).select_from(KBChunk))).scalar()

    assert len(sources) >= 10
    assert n == len(chunks)
    assert helico_chunks, "expected at least one chunk for the helicoverpa-zea page"
    # Tag enrichment: pest pages tag themselves + the host crops.
    assert "helicoverpa-zea" in helico_chunks[0].pests
    assert "corn" in helico_chunks[0].crops


async def test_ingest_is_idempotent(client, patch_embed):
    app = client.app
    factory = app.state.session_factory
    async with factory() as session:
        a = await ingest_wiki(session, api_key="x")
    async with factory() as session:
        b = await ingest_wiki(session, api_key="x")
    assert a == b
