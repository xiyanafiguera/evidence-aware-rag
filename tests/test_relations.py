from evidence_aware_rag.relations import RelationExpander


def ids(expansions):
    return [e.document_id for e in expansions]


def test_ticket_reaches_customer_and_contract_with_provenance(corpus):
    found = RelationExpander(corpus).expand(["INC-014"])
    assert set(ids(found)) == {"CUS-001", "CTR-001"}
    assert all(e.reason == "referenced_by INC-014 (hop 1)" for e in found)


def test_second_hop_follows_contract_to_pinned_policy(corpus):
    found = {e.document_id: e for e in RelationExpander(corpus).expand(["INC-015"])}
    assert found["SLA-001"].hop == 2 and found["SLA-001"].via == "CTR-002"


def test_max_hops_limits_depth(corpus):
    assert "SLA-001" not in ids(RelationExpander(corpus, max_hops=1).expand(["INC-015"]))


def test_seeds_are_never_re_added_and_budget_is_respected(corpus):
    found = RelationExpander(corpus, max_added=2).expand(["MTG-005", "MTG-003", "INC-018"])
    assert len(found) == 2
    assert not {"MTG-003", "MTG-005", "INC-018"} & set(ids(found))


def test_intent_priority_spends_budget_on_contracts_first(corpus):
    # Candidates: SLA-001, SLA-002, CTR-002 (from MTG-001) and CUS-001, CTR-001 (from INC-014).
    # Both contracts win the budget; between them, the one reached from the better-ranked seed first.
    found = RelationExpander(corpus, max_added=2).expand(
        ["MTG-001", "INC-014"], priority=["contract", "ticket", "policy", "crm"]
    )
    assert ids(found) == ["CTR-002", "CTR-001"]
