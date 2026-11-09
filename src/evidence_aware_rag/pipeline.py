"""Assemble an EvidencePackage from a query.

`build_pipeline` is the only place that knows which stages each evaluation mode uses:

| mode   | retrieval                       | relations | temporal | sufficiency |
|--------|---------------------------------|-----------|----------|-------------|
| bm25   | BM25                            | –         | –        | –           |
| dense  | Dense                           | –         | –        | –           |
| hybrid | RRF(BM25, Dense)                | –         | –        | –           |
| full   | RRF(Exact, BM25, Dense)         | ✓         | ✓        | ✓           |
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

from evidence_aware_rag.config import Settings
from evidence_aware_rag.corpus import Corpus
from evidence_aware_rag.index_store import IndexArtifacts, ensure_index
from evidence_aware_rag.models import ChunkRef, EvidenceItem, EvidencePackage, ScoredChunk, Sufficiency
from evidence_aware_rag.retrievers.base import Retriever, rank_documents
from evidence_aware_rag.retrievers.bm25 import BM25Retriever
from evidence_aware_rag.retrievers.dense import DenseRetriever, Embedder
from evidence_aware_rag.retrievers.hybrid import HybridRetriever

Mode = Literal["bm25", "dense", "hybrid", "full"]
MODES: tuple[Mode, ...] = ("bm25", "dense", "hybrid", "full")


@dataclass
class KnowledgeBase:
    """Everything loaded once per process and shared by all pipelines."""

    settings: Settings
    corpus: Corpus
    index: IndexArtifacts
    embedder: Embedder

    @classmethod
    def load(cls, settings: Settings | None = None) -> KnowledgeBase:
        settings = settings or Settings()
        corpus = Corpus.load(settings.data_dir)
        embedder = Embedder(settings)
        index, _ = ensure_index(corpus, settings, embedder)
        return cls(settings, corpus, index, embedder)


class EvidencePipeline:
    def __init__(self, kb: KnowledgeBase, retriever: Retriever, mode: str):
        self.kb = kb
        self.retriever = retriever
        self.mode = mode

    def run(self, query: str, as_of: date | None = None) -> EvidencePackage:
        settings = self.kb.settings
        hits = self.retriever.search(query, settings.chunk_candidates)
        ranking = rank_documents(hits)[: settings.top_k]
        evidence = [self._item(doc_id, hits, [f"retrieved: {self.retriever.name} rank {i}"])
                    for i, doc_id in enumerate(ranking, start=1)]
        return EvidencePackage(
            query=query,
            as_of_date=as_of,
            method=self.mode,
            intent=None,
            evidence=evidence,
            sufficiency=Sufficiency(status="unknown", reason=f"mode '{self.mode}' has no sufficiency rules"),
            retrieved_ranking=ranking,
        )

    def _item(self, doc_id: str, hits: list[ScoredChunk], why: list[str]) -> EvidenceItem:
        """Evidence entry with up to `max_chunks_per_doc` retrieved chunks (or the first chunk if none)."""
        doc = self.kb.corpus.get(doc_id)
        refs = [
            ChunkRef(chunk_id=h.chunk.chunk_id, section=h.chunk.section, text=h.chunk.text, source=h.source)
            for h in hits if h.chunk.document_id == doc_id
        ][: self.kb.settings.max_chunks_per_doc]
        if not refs:
            first = next(c for c in self.kb.index.chunks if c.document_id == doc_id)
            refs = [ChunkRef(chunk_id=first.chunk_id, section=first.section, text=first.text, source="expansion")]
        return EvidenceItem(document_id=doc_id, title=doc.meta.title, type=doc.meta.type, chunks=refs, why_included=why)


def build_pipeline(mode: Mode, kb: KnowledgeBase) -> EvidencePipeline:
    s = kb.settings
    bm25 = BM25Retriever(kb.index.chunks)
    dense = DenseRetriever(kb.index.chunks, kb.index.faiss_index, kb.embedder)
    if mode == "bm25":
        return EvidencePipeline(kb, bm25, mode)
    if mode == "dense":
        return EvidencePipeline(kb, dense, mode)
    if mode == "hybrid":
        return EvidencePipeline(kb, HybridRetriever([bm25, dense], s.rrf_k, s.chunk_candidates), mode)
    raise NotImplementedError(f"mode {mode!r} is not available yet")
