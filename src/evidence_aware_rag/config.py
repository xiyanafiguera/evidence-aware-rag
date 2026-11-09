"""Central settings: paths and retrieval parameters.

All tunable numbers live here so that the evaluation can record exactly which configuration
produced a result.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    root: Path = REPO_ROOT
    data_dir: Path = field(default=REPO_ROOT / "data")
    index_dir: Path = field(default=REPO_ROOT / "index")
    eval_dir: Path = field(default=REPO_ROOT / "eval")
    results_dir: Path = field(default=REPO_ROOT / "results")

    # Dense retrieval. The revision is pinned so that results are reproducible.
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_revision: str = "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a"
    query_instruction: str = "Represent this sentence for searching relevant passages: "

    # Retrieval
    rrf_k: int = 60
    chunk_candidates: int = 20  # chunks requested from each retriever before collapsing to documents
    top_k: int = 5  # documents kept from the ranking

    # Evidence package
    max_hops: int = 2
    max_expanded: int = 8
    max_chunks_per_doc: int = 3
