import pytest

from evidence_aware_rag.chunking import chunk_corpus
from evidence_aware_rag.retrievers.base import rank_documents
from evidence_aware_rag.retrievers.bm25 import BM25Retriever, tokenize


def test_tokenizer_keeps_identifiers_whole():
    assert tokenize("What caused INC-012 under SLA-002?") == ["caused", "inc-012", "under", "sla-002"]


def test_tokenizer_keeps_decimals_and_percentages():
    assert tokenize("availability 99.71% and 20%") == ["availability", "99.71%", "20%"]


@pytest.fixture(scope="module")
def bm25(corpus):
    return BM25Retriever(chunk_corpus(corpus))


def test_exact_ticket_id_ranks_its_document_first(bm25):
    assert rank_documents(bm25.search("INC-012", k=10))[0] == "INC-012"


def test_ranks_are_one_based_and_sorted(bm25):
    results = bm25.search("security incident notification", k=5)
    assert [r.rank for r in results] == list(range(1, len(results) + 1))
    assert all(a.score >= b.score for a, b in zip(results, results[1:]))


def test_query_without_known_terms_returns_nothing(bm25):
    assert bm25.search("zzzz qqqq", k=5) == []
