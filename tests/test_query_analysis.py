from datetime import date

import pytest

from evidence_aware_rag.chunking import chunk_corpus
from evidence_aware_rag.query_analysis import QueryAnalyzer, extract_dates
from evidence_aware_rag.retrievers.exact import ExactMatchRetriever


@pytest.fixture(scope="module")
def analyzer(corpus):
    return QueryAnalyzer(corpus)


def test_document_ids_are_found_case_insensitively_and_must_exist(analyzer):
    analysis = analyzer.analyze("Compare inc-014 with SLA-002 and XYZ-999")
    assert analysis.doc_ids == ["INC-014", "SLA-002"]


def test_customers_from_names_and_from_cited_documents(analyzer):
    assert analyzer.analyze("Does Acme Logistics get a credit?").customer_ids == ["CUS-002"]
    assert analyzer.analyze("What happened in INC-014?").customer_ids == ["CUS-001"]


@pytest.mark.parametrize("text, day, end", [
    ("on 2026-08-21", date(2026, 8, 21), None),
    ("on October 12, 2026", date(2026, 10, 12), None),
    ("on 12 Oct 2026", date(2026, 10, 12), None),
    ("in May 2026", date(2026, 5, 1), date(2026, 5, 31)),
    ("during Q3 2026", date(2026, 7, 1), date(2026, 9, 30)),
])
def test_date_formats(text, day, end):
    [mention] = extract_dates(text)
    assert (mention.day, mention.end) == (day, end)


def test_full_date_is_not_also_read_as_month(analyzer):
    assert len(extract_dates("on October 12, 2026")) == 1


def test_dates_without_year_are_ignored():
    assert extract_dates("the problem on October 28") == []


def test_compensation_intent_needs_a_concrete_subject(analyzer):
    assert analyzer.analyze("What compensation is Acme Corp entitled to for INC-014?").intent == "compensation"
    assert analyzer.analyze("What service credit does the standard SLA give at 99.7%?").intent is None


def test_exact_retriever_returns_cited_ids_then_named_customers(corpus, analyzer):
    exact = ExactMatchRetriever(chunk_corpus(corpus), analyzer)
    hits = exact.search("Is Corvid Health affected by INC-013?", k=5)
    assert [h.chunk.document_id for h in hits] == ["INC-013", "CUS-004"]
