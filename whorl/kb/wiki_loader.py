"""Load + chunk hand-authored markdown wiki pages from disk."""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class WikiPage:
    slug: str
    path: Path
    frontmatter: dict
    body: str

    @property
    def entity_kind(self) -> str:
        parts = {p.lower() for p in self.path.parts}
        if "pests" in parts:
            return "pest"
        if "crops" in parts:
            return "crop"
        if "products" in parts:
            return "product"
        if "moa" in parts:
            return "moa"
        if "alt-controls" in parts or "alt_controls" in parts:
            return "alt_control"
        if "regions" in parts:
            return "region"
        return "other"


_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)", re.DOTALL)


def parse_frontmatter(text: str) -> tuple[dict, str]:
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    fm = yaml.safe_load(m.group(1)) or {}
    return fm, m.group(2)


def load_wiki_pages(wiki_dir: Path) -> Iterator[WikiPage]:
    """Yield every wiki page except meta docs (schema/index/log)."""
    skip = {"schema.md", "index.md", "log.md"}
    for md in sorted(Path(wiki_dir).rglob("*.md")):
        if md.name in skip:
            continue
        text = md.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(text)
        slug = (fm.get("slug") if isinstance(fm, dict) else None) or md.stem
        yield WikiPage(slug=str(slug), path=md, frontmatter=fm or {}, body=body)


def chunk_text(text: str, *, target_size: int = 800, min_size: int = 120) -> list[str]:
    """Paragraph-aware chunker — combines adjacent paragraphs up to target_size."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current = ""
    for p in paragraphs:
        if not current:
            current = p
            continue
        if len(current) + len(p) + 2 <= target_size:
            current = f"{current}\n\n{p}"
        else:
            if len(current) >= min_size or not chunks:
                chunks.append(current)
            else:
                # Tiny tail — merge into previous chunk instead of emitting alone.
                chunks[-1] = f"{chunks[-1]}\n\n{current}"
            current = p
    if current:
        if len(current) >= min_size or not chunks:
            chunks.append(current)
        else:
            chunks[-1] = f"{chunks[-1]}\n\n{current}"
    return chunks
