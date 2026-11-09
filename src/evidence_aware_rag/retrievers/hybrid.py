"""Hybrid retrieval: Reciprocal Rank Fusion of several retrievers.

RRF combines positions, not raw scores, so BM25 scores and cosine similarities never need to be
calibrated against each other. The fused score is a ranking device, not a confidence.
"""

from __future__ import annotations

from collections import defaultdict

from evidence_aware_rag.models import ScoredChunk
from evidence_aware_rag.retrievers.base import Retriever


def rrf_fuse(rankings: list[list[ScoredChunk]], k: int = 60) -> list[ScoredChunk]:
    scores: dict[str, float] = defaultdict(float)
    chunks = {}
    for ranking in rankings:
        for scored in ranking:
            scores[scored.chunk.chunk_id] += 1.0 / (k + scored.rank)
            chunks.setdefault(scored.chunk.chunk_id, scored.chunk)
    order = sorted(scores, key=lambda cid: (-scores[cid], cid))
    return [
        ScoredChunk(chunk=chunks[cid], score=scores[cid], rank=rank, source="rrf")
        for rank, cid in enumerate(order, start=1)
    ]


class HybridRetriever:
    def __init__(self, retrievers: list[Retriever], rrf_k: int = 60, candidates: int = 20):
        self.retrievers = retrievers
        self.rrf_k = rrf_k
        self.candidates = candidates
        self.name = "+".join(r.name for r in retrievers)

    def search(self, query: str, k: int) -> list[ScoredChunk]:
        rankings = [r.search(query, self.candidates) for r in self.retrievers]
        return rrf_fuse(rankings, self.rrf_k)[:k]
