"""Ingest the hand-authored wiki — chunk + embed + insert into kb_chunks.

Idempotent: clears all `chunk_type='wiki'` rows + their kb_sources before
re-inserting, so `whorl kb ingest` always produces a consistent state.

Raw-source ingest (KSU MFs, IRAC v11.1, FRAC, etc.) lands in v0.4 when we
wire the per-source crawlers and the wiki-maintainer agent.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from whorl.config import get_settings
from whorl.db import init_db, make_engine, make_session_factory
from whorl.kb.embed import embed_texts
from whorl.kb.wiki_loader import WikiPage, chunk_text, load_wiki_pages
from whorl.models import KBChunk, KBSource

WIKI_DIR = Path(__file__).parent / "wiki"

log = logging.getLogger("whorl.kb.ingest")


def _to_list(v: Any) -> list[str]:
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x) for x in v if x is not None]
    if isinstance(v, str):
        return [v]
    return [str(v)]


def _tags_from_page(page: WikiPage) -> tuple[list[str], list[str], list[str], list[str]]:
    fm = page.frontmatter
    crops = _to_list(fm.get("hosts") or fm.get("crops"))
    if page.entity_kind == "crop":
        crops = _to_list(crops or [page.slug])
    pests = _to_list(fm.get("key_pests") or fm.get("targets"))
    if page.entity_kind == "pest":
        pests = list({*pests, page.slug})
    regions = _to_list(fm.get("regions"))
    if page.entity_kind == "region":
        # State pages tag themselves with both slug + state_code.
        state_code = fm.get("state_code")
        if state_code:
            regions = list({*regions, str(state_code)})
        regions = list({*regions, page.slug.upper(), page.slug})
    moa_groups: list[str] = []
    if page.entity_kind == "moa":
        cls = fm.get("moa_class")
        grp = fm.get("moa_group")
        if cls and grp is not None:
            moa_groups = [f"{cls}-{grp}"]
    return crops, pests, regions, moa_groups


def _title_for(page: WikiPage) -> str:
    fm = page.frontmatter
    return str(
        fm.get("name")
        or fm.get("scientific_name")
        or fm.get("state_name")
        or page.slug
    )


async def ingest_wiki(
    session: AsyncSession,
    *,
    api_key: str,
    wiki_dir: Path = WIKI_DIR,
    embedding_model: str | None = None,
) -> dict:
    """Wipe existing wiki rows and re-ingest all pages from disk."""
    # Idempotency: drop all wiki chunks + sources first.
    await session.execute(delete(KBChunk).where(KBChunk.chunk_type == "wiki"))
    await session.execute(delete(KBSource).where(KBSource.kind == "wiki"))
    await session.flush()

    page_count = 0
    chunk_count = 0

    for page in load_wiki_pages(wiki_dir):
        body = page.body.strip()
        if not body:
            continue

        source = KBSource(
            slug=page.slug,
            title=_title_for(page),
            publisher="Whorl wiki",
            url=None,
            license="AGPL-3.0",
            kind="wiki",
        )
        session.add(source)
        await session.flush()

        crops, pests, regions, moa_groups = _tags_from_page(page)
        chunks = chunk_text(body)
        if not chunks:
            continue

        kwargs = {"api_key": api_key}
        if embedding_model:
            kwargs["model"] = embedding_model
        embeddings = await embed_texts(chunks, **kwargs)

        for i, (text, emb) in enumerate(zip(chunks, embeddings, strict=True)):
            session.add(KBChunk(
                source_id=source.id,
                ordinal=i,
                text=text,
                embedding=emb,
                chunk_type="wiki",
                entity_kind=page.entity_kind,
                entity_slug=page.slug,
                crops=crops,
                pests=pests,
                regions=regions,
                moa_groups=moa_groups,
                citation=f"Whorl wiki · {page.entity_kind}/{page.slug}",
            ))
            chunk_count += 1
        page_count += 1

    await session.commit()
    return {"pages": page_count, "chunks": chunk_count}


async def main(database_url: str | None = None) -> None:
    settings = get_settings()
    url = database_url or settings.database_url
    engine = make_engine(url)
    try:
        await init_db(engine)
        async with make_session_factory(engine)() as session:
            stats = await ingest_wiki(session, api_key=settings.openrouter_api_key)
        print(f"ingested {stats['pages']} wiki pages → {stats['chunks']} chunks")
    finally:
        await engine.dispose()
