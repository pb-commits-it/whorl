"""Wiki loader + chunker."""

from __future__ import annotations

from pathlib import Path

from whorl.kb.wiki_loader import chunk_text, load_wiki_pages, parse_frontmatter


def test_parse_frontmatter_basic():
    text = """---
slug: helicoverpa-zea
common_names: [corn earworm, cotton bollworm]
taxonomy: {order: Lepidoptera, family: Noctuidae}
---

# Body starts here
Hello.
"""
    fm, body = parse_frontmatter(text)
    assert fm["slug"] == "helicoverpa-zea"
    assert fm["common_names"] == ["corn earworm", "cotton bollworm"]
    assert fm["taxonomy"]["family"] == "Noctuidae"
    assert body.startswith("# Body starts here")


def test_parse_frontmatter_no_frontmatter():
    fm, body = parse_frontmatter("just a body\nno frontmatter")
    assert fm == {}
    assert body == "just a body\nno frontmatter"


def test_chunk_text_paragraph_aware():
    paragraphs = ["para one " * 30, "para two " * 30, "para three " * 30]
    chunks = chunk_text("\n\n".join(paragraphs), target_size=400)
    assert len(chunks) >= 1
    assert all(len(c) <= 800 for c in chunks)
    joined = "\n\n".join(chunks)
    assert "para one" in joined
    assert "para three" in joined


def test_load_real_wiki_pages():
    wiki_dir = Path(__file__).resolve().parent.parent / "whorl" / "kb" / "wiki"
    pages = list(load_wiki_pages(wiki_dir))
    slugs = {p.slug for p in pages}
    # Spot-check that the corn-earworm scenario set is present.
    assert "helicoverpa-zea" in slugs
    assert "corn" in slugs
    assert "spinosad" in slugs
    assert "bifenthrin" in slugs
    assert "irac-3a" in slugs
    assert "irac-5" in slugs
    assert "irac-28" in slugs
    assert "bt-kurstaki" in slugs
    assert "kansas" in slugs

    helico = next(p for p in pages if p.slug == "helicoverpa-zea")
    assert helico.entity_kind == "pest"
    assert helico.frontmatter["scientific_name"] == "Helicoverpa zea"

    corn = next(p for p in pages if p.slug == "corn")
    assert corn.entity_kind == "crop"

    irac3a = next(p for p in pages if p.slug == "irac-3a")
    assert irac3a.entity_kind == "moa"
    assert irac3a.frontmatter["moa_group"] == "3A"
