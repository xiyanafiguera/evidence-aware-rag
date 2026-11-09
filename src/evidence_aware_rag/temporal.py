"""Decide which version of a policy governs a question.

Precedence, from strongest to weakest:

1. a contract **exception** for the customer (applies regardless of the policy version);
2. the customer's plan is **not covered** by the policy at all;
3. a contract **pin** to a specific version (while the pin is valid on the relevant date);
4. the version **in force** on the relevant date.

Dates are kept apart by role: the date of the *event* (an incident's `occurred_at`), dates *cited*
in the question, and the agent's `as_of` date (when the question is asked). The version is chosen by
event date, then cited date, then `as_of`. If content dates point to different versions, or there
is no date at all, the question is temporally ambiguous: every candidate version is returned, and a
clarification is flagged only if the candidates differ on the clauses the question is about.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from evidence_aware_rag.corpus import Corpus
from evidence_aware_rag.models import CandidateVersion, DateMention, Document, TemporalAssessment
from evidence_aware_rag.query_analysis import mentions


class TemporalResolver:
    def __init__(self, corpus: Corpus):
        self.corpus = corpus

    # --- public API ---------------------------------------------------------------------------

    def find_event(self, doc_ids: list[str], customer_id: str | None) -> DateMention | None:
        """The first ticket (in rank order) for the customer, as the event the question is about."""
        for doc_id in doc_ids:
            meta = self.corpus.meta(doc_id)
            if meta.type != "ticket" or meta.occurred_at is None:
                continue
            if customer_id is None or customer_id in meta.customer_ids:
                return DateMention(day=meta.occurred_at, source="event", detail=f"{doc_id} occurred_at")
        return None

    def resolve(self, family: str, dates: list[DateMention], customer_id: str | None = None,
                query: str = "") -> TemporalAssessment:
        versions = self.corpus.policy_versions(family)
        if not versions:
            raise KeyError(f"no versions for policy family {family!r}")
        contract = self.corpus.contract_for(customer_id) if customer_id else None
        base = dict(policy_family=family, dates_considered=dates)

        if contract:
            exception = next((e for e in contract.meta.exceptions if e.policy_family == family), None)
            if exception:
                return TemporalAssessment(
                    **base, relevant_date=self._primary(dates)[0], date_source=self._primary(dates)[1],
                    applicable=[contract.id], governed_by="contract_exception",
                    justification=f"{contract.id} defines an exception for {family}: {exception.rule}",
                )
            plans = versions[-1].meta.applies_to_plans
            if plans and contract.meta.plan not in plans:
                return TemporalAssessment(
                    **base, relevant_date=self._primary(dates)[0], date_source=self._primary(dates)[1],
                    applicable=[], governed_by="not_covered",
                    justification=f"{contract.id}: plan {contract.meta.plan} is not covered by {family} "
                                  f"(applies to {', '.join(plans)})",
                )

        notes: list[str] = []
        if customer_id and contract is None:
            notes.append(f"no contract found for {customer_id}: pins, exceptions and plan eligibility unverified")

        content = [d for d in dates if d.source in ("event", "question")]
        as_of = next((d for d in dates if d.source == "agent_as_of"), None)

        if content:
            options = {self._versions_for(d, contract, family) for d in content}
            chosen = next((d for d in content if d.source == "event"), content[0])
            if as_of and self._versions_for(as_of, contract, family) != self._versions_for(chosen, contract, family):
                notes.append(f"as_of_date {as_of.day} (query date) points to a different version than the "
                             f"referenced date {chosen.day}; the referenced date is used")
        elif as_of:
            options, chosen = {self._versions_for(as_of, contract, family)}, as_of
        elif self._pin(contract, family, None):
            options, chosen = {(self._pin(contract, family, None),)}, None  # the pin covers the whole term
        else:
            options, chosen = {tuple(d.id for d in versions)}, None

        candidates = sorted({doc_id for option in options for doc_id in option})
        relevant_date, date_source = (chosen.day, chosen.source) if chosen else (None, "none")

        if len(candidates) == 1:
            doc_id = candidates[0]
            pinned = self._pin(contract, family, relevant_date)
            governed_by = "contract_pin" if pinned == doc_id else "in_force"
            return TemporalAssessment(
                **base, relevant_date=relevant_date, date_source=date_source, applicable=[doc_id],
                governed_by=governed_by, justification=self._justify(doc_id, governed_by, contract, chosen),
                date_notes=notes,
            )

        terms = self._relevant_terms(family, query, candidates)
        differ = len({repr(t) for t in terms.values()}) > 1
        date_conflict = len(options) > 1
        reason = ("cited dates point to different versions" if date_conflict
                  else "a cited period spans several versions" if content
                  else "no date in the question")
        return TemporalAssessment(
            **base, relevant_date=relevant_date, date_source=date_source, applicable=[],
            governed_by="ambiguous",
            justification=f"{reason}: {len(candidates)} candidate versions; relevant terms "
                          f"{'differ' if differ else 'are identical'}",
            ambiguity_detected=True, date_conflict=date_conflict, clarification_needed=differ,
            candidate_interpretations=[
                CandidateVersion(document_id=c, valid_from=self.corpus.meta(c).valid_from,
                                 valid_to=self.corpus.meta(c).valid_to, relevant_terms=terms[c])
                for c in candidates
            ],
            date_notes=notes,
        )

    # --- helpers ------------------------------------------------------------------------------

    @staticmethod
    def _primary(dates: list[DateMention]) -> tuple[date | None, str]:
        for source in ("event", "question", "agent_as_of"):
            mention = next((d for d in dates if d.source == source), None)
            if mention:
                return mention.day, source
        return None, "none"

    @staticmethod
    def _pin(contract: Document | None, family: str, day: date | None) -> str | None:
        if not contract or family not in contract.meta.pinned_policies:
            return None
        pin = contract.meta.pinned_policies[family]
        return pin.document_id if day is None or day <= pin.until else None

    def _versions_for(self, mention: DateMention, contract: Document | None, family: str) -> tuple[str, ...]:
        """Versions governing a date mention; a month-level mention checks its first and last day."""
        days = [mention.day] + ([mention.end] if mention.end else [])
        found = []
        for day in days:
            pinned = self._pin(contract, family, day)
            if pinned:
                found.append(pinned)
                continue
            found += [v.id for v in self.corpus.policy_versions(family) if v.meta.in_force_on(day)]
        return tuple(sorted(set(found)))

    def _relevant_terms(self, family: str, query: str, candidates: list[str]) -> dict[str, dict[str, Any]]:
        """Each candidate's key terms, restricted to the clauses the query mentions (all if none)."""
        clauses = self.corpus.rules.policy_families[family].clauses
        relevant = [name for name, keywords in clauses.items() if any(mentions(query, k) for k in keywords)]
        result = {}
        for doc_id in candidates:
            key_terms = self.corpus.meta(doc_id).key_terms
            result[doc_id] = {c: key_terms.get(c) for c in (relevant or key_terms)}
        return result

    def _justify(self, doc_id: str, governed_by: str, contract: Document | None, chosen: DateMention | None) -> str:
        meta = self.corpus.meta(doc_id)
        when = f"{chosen.day} ({chosen.detail or chosen.source})" if chosen else "every date (single version)"
        if governed_by == "contract_pin":
            pin = contract.meta.pinned_policies[meta.policy_family]
            return f"{contract.id} pins {doc_id} until {pin.until}; relevant date {when}"
        validity = f"{meta.valid_from} → {meta.valid_to or 'open'}"
        return f"{doc_id} in force on {when} (valid {validity})"
