from datetime import date

import pytest

from evidence_aware_rag.models import DateMention
from evidence_aware_rag.temporal import TemporalResolver


@pytest.fixture(scope="module")
def resolver(corpus):
    return TemporalResolver(corpus)


def event(day: date) -> DateMention:
    return DateMention(day=day, source="event")


def cited(day: date, end: date | None = None) -> DateMention:
    return DateMention(day=day, end=end, source="question")


def as_of(day: date) -> DateMention:
    return DateMention(day=day, source="agent_as_of")


@pytest.mark.parametrize("day, expected", [
    (date(2026, 6, 30), "SLA-001"),  # last day of v1
    (date(2026, 7, 1), "SLA-002"),   # first day of v2
    (date(2026, 9, 30), "SLA-002"),
    (date(2026, 10, 1), "SLA-003"),  # v3 is open-ended
    (date(2027, 3, 1), "SLA-003"),
])
def test_version_in_force_at_boundaries(resolver, day, expected):
    result = resolver.resolve("service_sla", [cited(day)])
    assert (result.applicable, result.governed_by) == ([expected], "in_force")


def test_event_date_selects_version_for_incident(resolver):
    result = resolver.resolve("service_sla", [event(date(2026, 8, 21))], customer_id="CUS-001")
    assert result.applicable == ["SLA-002"] and result.date_source == "event"
    assert "SLA-002 in force on 2026-08-21" in result.justification


def test_contract_pin_overrides_version_in_force(resolver):
    result = resolver.resolve("service_sla", [event(date(2026, 9, 3))], customer_id="CUS-002")
    assert (result.applicable, result.governed_by) == (["SLA-001"], "contract_pin")


def test_pin_expires_after_its_end_date(resolver):
    result = resolver.resolve("service_sla", [cited(date(2026, 12, 20))], customer_id="CUS-002")
    assert (result.applicable, result.governed_by) == (["SLA-003"], "in_force")


def test_contract_exception_overrides_any_version(resolver):
    result = resolver.resolve("service_sla", [event(date(2026, 7, 22))], customer_id="CUS-004")
    assert (result.applicable, result.governed_by) == (["CTR-004"], "contract_exception")


def test_starter_plan_is_not_covered(resolver):
    result = resolver.resolve("service_sla", [event(date(2026, 6, 17))], customer_id="CUS-005")
    assert (result.applicable, result.governed_by) == ([], "not_covered")


def test_missing_contract_is_noted_not_hidden(resolver):
    result = resolver.resolve("service_sla", [event(date(2026, 10, 28))], customer_id="CUS-006")
    assert result.applicable == ["SLA-003"]
    assert any("no contract found" in note for note in result.date_notes)


def test_drafts_are_never_applicable(resolver):
    result = resolver.resolve("service_sla", [], query="credit")
    assert "DRF-001" not in [c.document_id for c in result.candidate_interpretations]


def test_no_date_with_differing_terms_needs_clarification(resolver):
    result = resolver.resolve("service_sla", [], query="What credit applies at 99.7% availability?")
    assert result.ambiguity_detected and result.clarification_needed
    assert [c.document_id for c in result.candidate_interpretations] == ["SLA-001", "SLA-002", "SLA-003"]
    assert result.applicable == []


def test_no_date_with_identical_relevant_clause_needs_no_clarification(resolver):
    result = resolver.resolve("refund_policy", [], query="How long do monthly customers have for a refund?")
    assert result.ambiguity_detected and not result.clarification_needed
    assert all(set(c.relevant_terms) == {"monthly_refund"} for c in result.candidate_interpretations)


def test_same_ambiguity_on_a_clause_that_changed_needs_clarification(resolver):
    result = resolver.resolve("refund_policy", [], query="Can an annual subscription be refunded?")
    assert result.clarification_needed


def test_month_spanning_a_version_change_is_ambiguous(resolver):
    # A fictional month-level mention covering the v1 → v2 boundary.
    result = resolver.resolve("service_sla", [cited(date(2026, 6, 15), end=date(2026, 7, 15))], query="credit")
    assert result.ambiguity_detected and not result.date_conflict


def test_conflicting_content_dates_are_flagged(resolver):
    dates = [event(date(2026, 8, 21)), cited(date(2026, 10, 12))]
    result = resolver.resolve("service_sla", dates, customer_id="CUS-001", query="credit")
    assert result.date_conflict and result.clarification_needed and result.applicable == []


def test_as_of_does_not_silently_override_a_referenced_date(resolver):
    dates = [event(date(2026, 8, 21)), as_of(date(2026, 11, 10))]
    result = resolver.resolve("service_sla", dates, customer_id="CUS-001")
    assert result.applicable == ["SLA-002"]
    assert any("as_of_date 2026-11-10" in note for note in result.date_notes)


def test_as_of_alone_selects_the_current_version_without_ambiguity(resolver):
    result = resolver.resolve("service_sla", [as_of(date(2026, 11, 10))], query="credit")
    assert result.applicable == ["SLA-003"] and not result.ambiguity_detected


def test_single_version_family_is_never_ambiguous(resolver):
    result = resolver.resolve("security_policy", [], query="notification")
    assert result.applicable == ["SEC-001"] and not result.ambiguity_detected


def test_find_event_prefers_the_customers_ticket(resolver):
    found = resolver.find_event(["INC-011", "INC-015", "INC-014"], customer_id="CUS-001")
    assert found.day == date(2026, 8, 21)
