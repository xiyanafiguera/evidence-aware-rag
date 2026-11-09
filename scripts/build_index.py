"""Build the retrieval index (skipped when data and model are unchanged).

Usage:
    uv run scripts/build_index.py [--force]
"""

from __future__ import annotations

import argparse
import time

from evidence_aware_rag.config import Settings
from evidence_aware_rag.corpus import Corpus
from evidence_aware_rag.index_store import ensure_index
from evidence_aware_rag.retrievers.dense import Embedder


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="rebuild even if the index is up to date")
    args = parser.parse_args()

    settings = Settings()
    corpus = Corpus.load(settings.data_dir)
    start = time.perf_counter()
    artifacts, rebuilt = ensure_index(corpus, settings, Embedder(settings), force=args.force)
    status = "built" if rebuilt else "up to date, skipped"
    print(f"index {status}: {len(artifacts.chunks)} chunks from {len(corpus)} documents "
          f"({time.perf_counter() - start:.1f}s) → {settings.index_dir}")


if __name__ == "__main__":
    main()
