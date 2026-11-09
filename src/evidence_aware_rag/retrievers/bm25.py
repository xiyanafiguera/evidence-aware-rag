"""Lexical retrieval with BM25.

The tokenizer keeps identifiers such as `INC-014` or `SLA-002` as single tokens: they are the
strongest lexical signal in enterprise text and a naive tokenizer would split them into "inc" and
"014", which match everything.
"""

from __future__ import annotations

import re

from rank_bm25 import BM25Okapi

from evidence_aware_rag.models import Chunk, ScoredChunk

TOKEN = re.compile(r"[a-z]+-\d+|\d+(?:\.\d+)?%?|[a-z0-9_]+")
STOPWORDS = frozenset(
    "a an and are as at be by can could did do does for from has have how i if in is it its "
    "of on or our should that the their them they this to was we were what when which who why "
    "will with would you your".split()
)


def tokenize(text: str) -> list[str]:
    return [t for t in TOKEN.findall(text.lower()) if t not in STOPWORDS]


class BM25Retriever:
    name = "bm25"

    def __init__(self, chunks: list[Chunk]):
        self.chunks = chunks
        self._bm25 = BM25Okapi([tokenize(c.text) for c in chunks])

    def search(self, query: str, k: int) -> list[ScoredChunk]:
        scores = self._bm25.get_scores(tokenize(query))
        # Ties are broken by chunk_id so that results are deterministic.
        order = sorted(range(len(self.chunks)), key=lambda i: (-scores[i], self.chunks[i].chunk_id))
        return [
            ScoredChunk(chunk=self.chunks[i], score=float(scores[i]), rank=rank, source=self.name)
            for rank, i in enumerate(order[:k], start=1)
            if scores[i] > 0
        ]
