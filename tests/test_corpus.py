from datetime import date

from evidence_aware_rag.chunking import chunk_corpus, chunk_document


def test_loads_every_manifest_document(corpus):
    assert len(corpus) == 35
    assert corpus.get("INC-014").meta.occurred_at == date(2026, 8, 21)


def test_json_records_are_rendered_as_text(corpus):
    text = corpus.get("INC-014").text
    assert "customer name: Acme Corp" in text
    assert "connection pool saturation" in text.lower()


def test_policy_versions_exclude_drafts_unless_asked(corpus):
    assert [d.id for d in corpus.policy_versions("service_sla")] == ["SLA-001", "SLA-002", "SLA-003"]
    assert "DRF-001" in [d.id for d in corpus.policy_versions("service_sla", include_drafts=True)]


def test_in_force_on_includes_both_boundaries(corpus):
    sla2 = corpus.meta("SLA-002")
    assert sla2.in_force_on(date(2026, 7, 1))
    assert sla2.in_force_on(date(2026, 9, 30))
    assert not sla2.in_force_on(date(2026, 10, 1))
    assert not corpus.meta("DRF-001").in_force_on(date(2026, 10, 1))


def test_contract_lookup_and_missing_contract(corpus):
    assert corpus.contract_for("CUS-002").id == "CTR-002"
    assert corpus.contract_for("CUS-006") is None


def test_entity_aliases_keep_similar_names_apart(corpus):
    assert corpus.entity_aliases["acme corp"] == "CUS-001"
    assert corpus.entity_aliases["acme logistics"] == "CUS-002"


def test_markdown_sections_become_chunks_prefixed_with_title(corpus):
    chunks = chunk_document(corpus.get("SLA-003"))
    sections = [c.section for c in chunks]
    assert sections[0] is None  # preamble with title and Document ID
    assert "Service credits" in sections
    credits = next(c for c in chunks if c.section == "Service credits")
    assert credits.text.startswith("Service Level Agreement v3 — Service credits")


def test_chunk_ids_are_unique_and_point_to_real_documents(corpus):
    chunks = chunk_corpus(corpus)
    assert len({c.chunk_id for c in chunks}) == len(chunks)
    assert all(c.document_id in corpus for c in chunks)
