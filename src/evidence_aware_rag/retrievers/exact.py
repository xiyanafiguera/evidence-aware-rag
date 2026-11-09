"""Exact matching of identifiers and entity names written in the query.

`INC-014` or "Corvid Health" in a question is a precise pointer; no ranking model should be able
to push that document out of the results.
"""

from __future__ import annotations

from evidence_aware_rag.models import Chunk, ScoredChunk
from evidence_aware_rag.query_analysis import QueryAnalyzer, mentions


class ExactMatchRetriever:
    name = "exact"

    def __init__(self, chunks: list[Chunk], analyzer: QueryAnalyzer):
        self.analyzer = analyzer
        self._first_chunk: dict[str, Chunk] = {}
        for chunk in chunks:
            self._first_chunk.setdefault(chunk.document_id, chunk)

    def search(self, query: str, k: int) -> list[ScoredChunk]:
        analysis = self.analyzer.analyze(query)
        named = [cid for name, cid in self.analyzer.corpus.entity_aliases.items() if mentions(query, name)]
        doc_ids = list(dict.fromkeys(analysis.doc_ids + named))
        return [
            ScoredChunk(chunk=self._first_chunk[doc_id], score=1.0, rank=rank, source=self.name)
            for rank, doc_id in enumerate(doc_ids[:k], start=1)
            if doc_id in self._first_chunk
        ]
