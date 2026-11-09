from datetime import date

import pytest

from evidence_aware_rag.pipeline import KnowledgeBase, build_pipeline


@pytest.fixture(scope="module")
def full():
    return build_pipeline("full", KnowledgeBase.load())


def by_id(package):
    return {item.document_id: item for item in package.evidence}


def test_compensation_case_is_sufficient_and_names_the_governing_version(full):
    package = full.run("What compensation is Acme Corp entitled to for INC-014?")
    assert package.intent == "compensation"
    assert package.sufficiency.status == "sufficient"
    [assessment] = package.temporal
    assert (assessment.applicable, assessment.governed_by) == (["SLA-002"], "in_force")
    assert package.evidence[0].document_id == "SLA-002"  # governing documents come first


def test_missing_contract_makes_evidence_insufficient(full):
    package = full.run("What credit should Everfield Retail receive for the dashboard problem on October 28?")
    assert package.sufficiency.status == "insufficient"
    assert package.sufficiency.missing == ["contract"]


def test_questions_without_rules_are_unknown_not_sufficient(full):
    assert full.run("How much revenue did Northstar Cloud lose in Q3 2026?").sufficiency.status == "unknown"


def test_drafts_and_superseded_versions_are_labelled(full):
    package = full.run("What service credit does the standard SLA give when monthly availability is 99.7%?")
    items = by_id(package)
    assert items["DRF-001"].version_status == "draft"
    assert {items[d].version_status for d in ("SLA-001", "SLA-002", "SLA-003")} == {"candidate"}
    assert package.clarification_needed


def test_every_evidence_item_explains_why_it_is_there(full):
    package = full.run("Acme Logistics wants a credit for the webhook delays in September 2026.")
    assert all(item.why_included for item in package.evidence)
    assert all(1 <= len(item.chunks) <= 3 for item in package.evidence)


def test_agent_as_of_is_recorded_when_it_differs(full):
    package = full.run("What compensation is Acme Corp entitled to for INC-014?", as_of=date(2026, 11, 10))
    [assessment] = package.temporal
    assert assessment.applicable == ["SLA-002"]
    assert assessment.date_notes
