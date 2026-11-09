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
from evidence_aware_rag.models import (
    ChunkRef, DateMention, EvidenceItem, EvidencePackage, ScoredChunk, Sufficiency, TemporalAssessment,
)
from evidence_aware_rag.query_analysis import QueryAnalysis, QueryAnalyzer, mentions
from evidence_aware_rag.relations import RelationExpander
from evidence_aware_rag.retrievers.base import Retriever, rank_documents
from evidence_aware_rag.retrievers.bm25 import BM25Retriever
from evidence_aware_rag.retrievers.dense import DenseRetriever, Embedder
from evidence_aware_rag.retrievers.exact import ExactMatchRetriever
from evidence_aware_rag.retrievers.hybrid import HybridRetriever
from evidence_aware_rag.sufficiency import SufficiencyChecker
from evidence_aware_rag.temporal import TemporalResolver

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
    """Retrieval, then (optionally) relation expansion, temporal resolution and sufficiency."""

    def __init__(self, kb: KnowledgeBase, retriever: Retriever, mode: str, *,
                 analyzer: QueryAnalyzer | None = None, expander: RelationExpander | None = None,
                 resolver: TemporalResolver | None = None, checker: SufficiencyChecker | None = None):
        self.kb = kb
        self.retriever = retriever
        self.mode = mode
        self.analyzer = analyzer
        self.expander = expander
        self.resolver = resolver
        self.checker = checker

    def run(self, query: str, as_of: date | None = None) -> EvidencePackage:
        settings, corpus = self.kb.settings, self.kb.corpus
        hits = self.retriever.search(query, settings.chunk_candidates)
        ranking = rank_documents(hits)[: settings.top_k]
        why: dict[str, list[str]] = {d: [f"retrieved: {self.retriever.name} rank {i}"]
                                     for i, d in enumerate(ranking, start=1)}

        analysis = self.analyzer.analyze(query) if self.analyzer else None
        intent_rules = corpus.rules.intents.get(analysis.intent) if analysis and analysis.intent else None

        if self.expander:
            priority = intent_rules.expansion_priority if intent_rules else None
            for expansion in self.expander.expand(ranking, priority):
                why.setdefault(expansion.document_id, []).append(expansion.reason)

        temporal: list[TemporalAssessment] = []
        if self.resolver and analysis:
            temporal = self._resolve_versions(analysis, ranking, list(why), as_of)
            for assessment in temporal:
                for doc_id in assessment.applicable:
                    why.setdefault(doc_id, []).append(f"governing document ({assessment.governed_by}): "
                                                      f"{assessment.justification}")
                for candidate in assessment.candidate_interpretations:
                    why.setdefault(candidate.document_id, []).append("candidate version (temporally ambiguous)")

        sufficiency = (self.checker.check(analysis, list(why), temporal) if self.checker and analysis
                       else Sufficiency(status="unknown", reason=f"mode '{self.mode}' has no sufficiency rules"))

        evidence = [self._item(doc_id, hits, reasons) for doc_id, reasons in why.items()]
        self._mark_versions(evidence, temporal)
        evidence.sort(key=lambda item: item.version_status != "applicable")  # stable: governing docs first
        return EvidencePackage(
            query=query,
            as_of_date=as_of,
            method=self.mode,
            intent=analysis.intent if analysis else None,
            evidence=evidence,
            temporal=temporal,
            sufficiency=sufficiency,
            retrieved_ranking=ranking,
        )

    def _resolve_versions(self, analysis: QueryAnalysis, ranking: list[str], evidence_ids: list[str],
                          as_of: date | None) -> list[TemporalAssessment]:
        """Assess the intent's policy family, plus families the query asks about explicitly.

        A family counts as "asked about" when one of its documents is retrieved *and* the query
        mentions one of its clauses; this keeps non-temporal questions free of spurious flags.
        """
        corpus = self.kb.corpus
        families: list[str] = []
        if analysis.intent and corpus.rules.intents[analysis.intent].policy_family:
            families.append(corpus.rules.intents[analysis.intent].policy_family)
        for doc_id in ranking:
            family = corpus.meta(doc_id).policy_family
            if family and family not in families:
                clauses = corpus.rules.policy_families[family].clauses.values()
                if any(mentions(analysis.query, kw) for keywords in clauses for kw in keywords):
                    families.append(family)

        customer = analysis.customer_ids[0] if analysis.customer_ids else None
        dates: list[DateMention] = []
        if customer:
            event = self.resolver.find_event(analysis.doc_ids + evidence_ids, customer)
            if event:
                dates.append(event)
        dates += analysis.dates
        if as_of:
            dates.append(DateMention(day=as_of, source="agent_as_of", detail="as_of_date"))
        return [self.resolver.resolve(f, dates, customer, analysis.query) for f in families]

    def _mark_versions(self, evidence: list[EvidenceItem], temporal: list[TemporalAssessment]) -> None:
        corpus = self.kb.corpus
        for item in evidence:
            meta = corpus.meta(item.document_id)
            if meta.status == "draft":
                item.version_status = "draft"
            for assessment in temporal:
                if item.document_id in assessment.applicable:
                    item.version_status = "applicable"
                elif item.document_id in {c.document_id for c in assessment.candidate_interpretations}:
                    item.version_status = "candidate"
                elif meta.policy_family == assessment.policy_family and meta.status != "draft":
                    item.version_status = "not_applicable"

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
    if mode == "full":
        analyzer = QueryAnalyzer(kb.corpus)
        exact = ExactMatchRetriever(kb.index.chunks, analyzer)
        return EvidencePipeline(
            kb, HybridRetriever([exact, bm25, dense], s.rrf_k, s.chunk_candidates), mode,
            analyzer=analyzer,
            expander=RelationExpander(kb.corpus, s.max_hops, s.max_expanded),
            resolver=TemporalResolver(kb.corpus),
            checker=SufficiencyChecker(kb.corpus),
        )
    raise ValueError(f"unknown mode {mode!r}; expected one of {MODES}")
