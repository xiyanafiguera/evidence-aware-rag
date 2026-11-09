"""Structural sufficiency: is every piece an answer needs actually present?

Conservative by design. Only intents with declared requirements (in `data/domain_rules.json`) can
be judged `sufficient` or `insufficient`; anything else is `unknown`. Retrieval scores are never
used here: a high RRF score says a document is relevant, not that the evidence is complete.
"""

from __future__ import annotations

from evidence_aware_rag.corpus import Corpus
from evidence_aware_rag.models import Sufficiency, TemporalAssessment
from evidence_aware_rag.query_analysis import QueryAnalysis


class SufficiencyChecker:
    def __init__(self, corpus: Corpus):
        self.corpus = corpus

    def check(self, analysis: QueryAnalysis, evidence_ids: list[str],
              temporal: list[TemporalAssessment]) -> Sufficiency:
        if analysis.intent is None:
            return Sufficiency(status="unknown", reason="no sufficiency rules for this kind of question")

        rules = self.corpus.rules.intents[analysis.intent]
        customer = analysis.customer_ids[0]
        missing, found = [], []

        if "incident" in rules.requires:
            tickets = [d for d in evidence_ids
                       if self.corpus.meta(d).type == "ticket" and customer in self.corpus.meta(d).customer_ids
                       and self.corpus.meta(d).occurred_at]
            (found if tickets else missing).append("incident" if not tickets else f"incident {tickets[0]}")

        if "contract" in rules.requires:
            contract = self.corpus.contract_for(customer)
            if contract is None:
                missing.append("contract")
            else:
                found.append(f"contract {contract.id}")

        if "applicable_policy" in rules.requires:
            assessment = next((t for t in temporal if t.policy_family == rules.policy_family), None)
            if assessment is None or assessment.governed_by in ("ambiguous", "unresolved"):
                missing.append("applicable_policy")
            elif "contract" not in missing:
                governing = ", ".join(assessment.applicable) or "none (plan not covered)"
                found.append(f"{rules.policy_family}: {governing} ({assessment.governed_by})")

        if missing:
            return Sufficiency(status="insufficient", missing=missing,
                               reason=f"{analysis.intent} for {customer} requires {', '.join(rules.requires)}; "
                                      f"missing: {', '.join(missing)}")
        return Sufficiency(status="sufficient",
                           reason=f"{analysis.intent} for {customer}: found {'; '.join(found)}")
