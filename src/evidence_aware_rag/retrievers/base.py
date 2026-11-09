"""The retriever interface and the helper that turns chunk rankings into document rankings."""

from __future__ import annotations

from typing import Protocol

from evidence_aware_rag.models import ScoredChunk


class Retriever(Protocol):
    name: str

    def search(self, query: str, k: int) -> list[ScoredChunk]:
        """Return up to `k` chunks, best first, with 1-based ranks."""
        ...


def rank_documents(chunks: list[ScoredChunk]) -> list[str]:
    """Collapse a chunk ranking into a document ranking (a document ranks by its best chunk)."""
    seen: dict[str, None] = {}
    for scored in chunks:
        seen.setdefault(scored.chunk.document_id, None)
    return list(seen)
