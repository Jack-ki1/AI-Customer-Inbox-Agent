"""
retrieval.py
------------
"Knowledge retrieval" step of the pipeline:

    Intent detection -> [Knowledge retrieval] -> Response generation

For an "intentionally simple" automation we implement retrieval with
scikit-learn's TF-IDF + cosine similarity over the business's own knowledge
base files (data/knowledge_base/*.md). This needs no external API call, no
vector database, and no cost - it just works the moment you run the app.

Production upgrade path (as referenced in the original spec):
    Replace `KnowledgeBase.search()` with an embeddings-based search:
      1. Embed each chunk once with OpenAI/Gemini/Claude embeddings (or any
         sentence-transformers model) and store the vectors in Postgres +
         pgvector (`CREATE EXTENSION vector;`, `ORDER BY embedding <=> query`).
      2. Embed the incoming question the same way and query pgvector for the
         nearest chunks instead of using TF-IDF.
    The rest of the pipeline (intent detection, response generation, lead
    capture) does not need to change - this class is a drop-in seam.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@dataclass
class Chunk:
    source: str
    heading: str
    text: str


def _split_markdown_into_chunks(path: Path) -> List[Chunk]:
    """Split a markdown FAQ file into chunks by '## Heading' sections."""
    raw = path.read_text(encoding="utf-8")
    sections = re.split(r"\n(?=## )", raw)
    chunks = []
    for section in sections:
        section = section.strip()
        if not section:
            continue
        first_line = section.splitlines()[0].lstrip("# ").strip()
        chunks.append(Chunk(source=path.name, heading=first_line, text=section))
    return chunks


class KnowledgeBase:
    def __init__(self, kb_dir: Path = DATA_DIR / "knowledge_base"):
        self.kb_dir = kb_dir
        self.business_profile = json.loads((DATA_DIR / "business_profile.json").read_text())
        self.chunks: List[Chunk] = []

        # Fold the business profile itself into a retrievable chunk.
        profile_text = (
            f"Business: {self.business_profile['name']}\n"
            f"Hours: {self.business_profile['hours']}\n"
            f"Location: {self.business_profile['location']}\n"
            f"Contact: {self.business_profile['phone']} / {self.business_profile['email']}\n"
            f"Services: {', '.join(self.business_profile['services'])}\n"
            f"Booking note: {self.business_profile['booking_note']}"
        )
        self.chunks.append(Chunk(source="business_profile.json", heading="Business Info", text=profile_text))

        for md_file in sorted(self.kb_dir.glob("*.md")):
            self.chunks.extend(_split_markdown_into_chunks(md_file))

        self._texts = [c.text for c in self.chunks]
        self._vectorizer = TfidfVectorizer(stop_words="english")
        self._matrix = self._vectorizer.fit_transform(self._texts)

    def search(self, query: str, top_k: int = 3) -> List[Chunk]:
        query_vec = self._vectorizer.transform([query])
        sims = cosine_similarity(query_vec, self._matrix).flatten()
        ranked_idx = sims.argsort()[::-1][:top_k]
        # Filter out near-zero matches (keeps context tight when the KB truly
        # doesn't cover the topic - the LLM should say "let me check" instead
        # of forcing an unrelated chunk into the prompt).
        return [self.chunks[i] for i in ranked_idx if sims[i] > 0.03] or [self.chunks[0]]

    def context_block(self, query: str, top_k: int = 3) -> str:
        hits = self.search(query, top_k=top_k)
        return "\n\n---\n\n".join(f"[{c.source} | {c.heading}]\n{c.text}" for c in hits)


# Singleton instance the app imports.
knowledge_base = KnowledgeBase()
