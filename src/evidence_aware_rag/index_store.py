"""Build, persist and load the retrieval index.

The fingerprint covers the chunk texts and the embedding model revision, so the index is rebuilt
whenever the data or the chunking changes, and never otherwise.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from typing import Any

from evidence_aware_rag.chunking import chunk_corpus
from evidence_aware_rag.config import Settings
from evidence_aware_rag.corpus import Corpus
from evidence_aware_rag.models import Chunk
from evidence_aware_rag.retrievers.dense import Embedder, build_faiss_index, load_faiss_index, save_faiss_index

log = logging.getLogger(__name__)

CHUNKS_FILE = "chunks.json"
VECTORS_FILE = "embeddings.faiss"
META_FILE = "meta.json"


@dataclass
class IndexArtifacts:
    chunks: list[Chunk]
    faiss_index: Any  # faiss.Index (faiss is only imported in retrievers/dense.py)
    fingerprint: str


def fingerprint(chunks: list[Chunk], settings: Settings) -> str:
    digest = hashlib.sha256()
    digest.update(f"{settings.embedding_model}@{settings.embedding_revision}".encode())
    for chunk in chunks:
        digest.update(chunk.chunk_id.encode())
        digest.update(chunk.text.encode())
    return digest.hexdigest()


def stored_fingerprint(settings: Settings) -> str | None:
    meta_path = settings.index_dir / META_FILE
    if not meta_path.exists():
        return None
    return json.loads(meta_path.read_text(encoding="utf-8")).get("fingerprint")


def build(corpus: Corpus, settings: Settings, embedder: Embedder) -> IndexArtifacts:
    chunks = chunk_corpus(corpus)
    vectors = embedder.embed_passages([c.text for c in chunks])
    artifacts = IndexArtifacts(chunks, build_faiss_index(vectors), fingerprint(chunks, settings))

    settings.index_dir.mkdir(parents=True, exist_ok=True)
    (settings.index_dir / CHUNKS_FILE).write_text(
        json.dumps([c.model_dump() for c in chunks], indent=1), encoding="utf-8"
    )
    save_faiss_index(artifacts.faiss_index, settings.index_dir / VECTORS_FILE)
    (settings.index_dir / META_FILE).write_text(json.dumps({
        "fingerprint": artifacts.fingerprint,
        "embedding_model": settings.embedding_model,
        "embedding_revision": settings.embedding_revision,
        "chunks": len(chunks),
        "dimensions": int(vectors.shape[1]),
    }, indent=2), encoding="utf-8")
    log.info("built index: %d chunks", len(chunks))
    return artifacts


def load(settings: Settings) -> IndexArtifacts:
    raw = json.loads((settings.index_dir / CHUNKS_FILE).read_text(encoding="utf-8"))
    chunks = [Chunk.model_validate(c) for c in raw]
    index = load_faiss_index(settings.index_dir / VECTORS_FILE)
    return IndexArtifacts(chunks, index, stored_fingerprint(settings) or "")


def ensure_index(corpus: Corpus, settings: Settings, embedder: Embedder, force: bool = False) -> tuple[IndexArtifacts, bool]:
    """Load the stored index if it matches the current data, otherwise rebuild it.

    Returns the artifacts and whether a rebuild happened.
    """
    current = fingerprint(chunk_corpus(corpus), settings)
    if not force and stored_fingerprint(settings) == current:
        return load(settings), False
    return build(corpus, settings, embedder), True
