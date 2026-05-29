"""Knowledge base — Karpathy llm-wiki pattern (kb/wiki) + raw RAG over kb_chunks."""

from whorl.kb.embed import embed_texts
from whorl.kb.rag import retrieve_wiki
from whorl.kb.wiki_loader import WikiPage, chunk_text, load_wiki_pages

__all__ = ["WikiPage", "chunk_text", "embed_texts", "load_wiki_pages", "retrieve_wiki"]
