"""Relation-based expansion: follow explicit references from the retrieved documents.

This is deterministic graph traversal over `references` in the manifest (ticket → customer →
contract → pinned policy, ...), not learned multi-hop reasoning. Depth and the number of added
documents are capped, and every added document records the path that brought it in.
"""

from __future__ import annotations

from dataclasses import dataclass

from evidence_aware_rag.corpus import Corpus
from evidence_aware_rag.models import DocType


@dataclass(frozen=True)
class Expansion:
    document_id: str
    hop: int
    via: str  # the document whose reference added this one
    seed_rank: int  # rank of the retrieved document the path started from

    @property
    def reason(self) -> str:
        return f"referenced_by {self.via} (hop {self.hop})"


class RelationExpander:
    def __init__(self, corpus: Corpus, max_hops: int = 2, max_added: int = 8):
        self.corpus = corpus
        self.max_hops = max_hops
        self.max_added = max_added

    def expand(self, seed_ids: list[str], priority: list[DocType] | None = None) -> list[Expansion]:
        """Documents reachable from `seed_ids` (ordered by rank), best first, capped at `max_added`.

        Ordering: document-type priority for the detected intent (e.g. contracts before meeting
        notes for a compensation question), then fewer hops, then the rank of the seed.
        """
        known = set(seed_ids)
        frontier = [(doc_id, rank) for rank, doc_id in enumerate(seed_ids, start=1)]
        found: list[Expansion] = []
        for hop in range(1, self.max_hops + 1):
            next_frontier = []
            for source, seed_rank in frontier:
                for target in self.corpus.meta(source).references:
                    if target in known or target not in self.corpus:
                        continue
                    known.add(target)
                    found.append(Expansion(target, hop, source, seed_rank))
                    next_frontier.append((target, seed_rank))
            frontier = next_frontier

        def order(e: Expansion) -> tuple:
            doc_type = self.corpus.meta(e.document_id).type
            type_rank = priority.index(doc_type) if priority and doc_type in priority else len(priority or [])
            return type_rank, e.hop, e.seed_rank, e.document_id

        return sorted(found, key=order)[: self.max_added]
