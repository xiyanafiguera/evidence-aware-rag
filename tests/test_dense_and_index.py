import dataclasses
from pathlib import Path

import numpy as np
import pytest

from evidence_aware_rag import index_store
from evidence_aware_rag.retrievers.base import rank_documents
from evidence_aware_rag.retrievers.dense import DenseRetriever, Embedder

PACKAGE_DIR = Path(__file__).resolve().parents[1] / "src" / "evidence_aware_rag"


class FakeModel:
    """Records what is encoded; returns deterministic unit vectors."""

    def __init__(self):
        self.seen: list[str] = []

    def encode(self, texts, **_):
        self.seen.extend(texts)
        vectors = np.ones((len(texts), 8), dtype=np.float32)
        return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)


def fake_embedder(settings) -> Embedder:
    embedder = Embedder(settings)
    embedder._model = FakeModel()
    return embedder


def test_query_instruction_is_added_to_queries_only(settings):
    embedder = fake_embedder(settings)
    embedder.embed_passages(["a passage"])
    embedder.embed_query("a question")
    assert embedder.model.seen == ["a passage", settings.query_instruction + "a question"]


def test_index_is_rebuilt_only_when_data_changes(corpus, settings, tmp_path):
    local = dataclasses.replace(settings, index_dir=tmp_path)
    _, rebuilt = index_store.ensure_index(corpus, local, fake_embedder(local))
    assert rebuilt
    _, rebuilt = index_store.ensure_index(corpus, local, fake_embedder(local))
    assert not rebuilt
    _, rebuilt = index_store.ensure_index(corpus, local, fake_embedder(local), force=True)
    assert rebuilt


def test_faiss_imported_only_in_dense_module():
    """faiss must be imported after torch (macOS OpenMP clash); keep that import in one place."""
    offenders = [
        p.relative_to(PACKAGE_DIR).as_posix()
        for p in PACKAGE_DIR.rglob("*.py")
        if "import faiss" in p.read_text() and p.name != "dense.py"
    ]
    assert offenders == []


@pytest.fixture(scope="module")
def dense(corpus, settings):
    artifacts, _ = index_store.ensure_index(corpus, settings, Embedder(settings))
    return DenseRetriever(artifacts.chunks, artifacts.faiss_index, Embedder(settings))


def test_dense_finds_paraphrased_incident(dense):
    """No document says 'requests failing'; the ticket talks about 5xx errors and a connection pool."""
    top = rank_documents(dense.search("Why did Acme Corp's requests start failing in late August?", k=20))[:5]
    assert "INC-014" in top
