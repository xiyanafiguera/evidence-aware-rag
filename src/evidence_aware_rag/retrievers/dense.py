"""Dense retrieval with BGE embeddings and an exact FAISS inner-product index.

This is the only module that imports `faiss`. On macOS, faiss-cpu and torch ship separate OpenMP
runtimes, and importing faiss *before* torch makes the first model forward pass segfault.
Importing torch first avoids it, so keep this order and keep faiss imports here.
"""

from __future__ import annotations

from pathlib import Path

import torch  # noqa: F401  (must be imported before faiss, see module docstring)
import faiss
import numpy as np

from evidence_aware_rag.config import Settings
from evidence_aware_rag.models import Chunk, ScoredChunk


class Embedder:
    """Wraps the sentence-transformers model; loaded lazily, once per process.

    BGE v1.5 expects an instruction prefix on queries only, never on the passages.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self._model = None

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer  # heavy import, deferred

            self._model = SentenceTransformer(
                self.settings.embedding_model, revision=self.settings.embedding_revision, device="cpu"
            )
        return self._model

    def embed_passages(self, texts: list[str]) -> np.ndarray:
        return self.model.encode(texts, batch_size=32, normalize_embeddings=True, convert_to_numpy=True)

    def embed_query(self, query: str) -> np.ndarray:
        return self.model.encode(
            [self.settings.query_instruction + query], normalize_embeddings=True, convert_to_numpy=True
        )


def build_faiss_index(embeddings: np.ndarray) -> faiss.Index:
    index = faiss.IndexFlatIP(embeddings.shape[1])  # exact search; cosine because vectors are normalized
    index.add(embeddings.astype(np.float32))
    return index


def save_faiss_index(index: faiss.Index, path: Path) -> None:
    faiss.write_index(index, str(path))


def load_faiss_index(path: Path) -> faiss.Index:
    return faiss.read_index(str(path))


class DenseRetriever:
    name = "dense"

    def __init__(self, chunks: list[Chunk], index: faiss.Index, embedder: Embedder):
        if index.ntotal != len(chunks):
            raise ValueError(f"index has {index.ntotal} vectors but there are {len(chunks)} chunks; rebuild the index")
        self.chunks = chunks
        self.index = index
        self.embedder = embedder

    def search(self, query: str, k: int) -> list[ScoredChunk]:
        scores, ids = self.index.search(self.embedder.embed_query(query).astype(np.float32), k)
        return [
            ScoredChunk(chunk=self.chunks[i], score=float(s), rank=rank, source=self.name)
            for rank, (s, i) in enumerate(zip(scores[0], ids[0]), start=1)
            if i >= 0
        ]
