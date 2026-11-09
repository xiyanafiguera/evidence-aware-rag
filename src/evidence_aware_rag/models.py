"""Data models shared across the package.

Pydantic is used for data that crosses a boundary: the manifest, the domain rules, evaluation
questions, and the EvidencePackage returned to agents.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field

DocType = Literal["policy", "policy_draft", "contract", "ticket", "crm", "meeting", "marketing", "runbook"]
VersionStatus = Literal["applicable", "candidate", "not_applicable", "draft", "n/a"]
GovernedBy = Literal["contract_exception", "contract_pin", "in_force", "not_covered", "ambiguous", "unresolved"]


# --- Manifest -------------------------------------------------------------------------------


class PinnedPolicy(BaseModel):
    document_id: str
    until: date


class PolicyException(BaseModel):
    policy_family: str
    rule: str
    key_terms: dict[str, Any] = {}


class DocumentMeta(BaseModel):
    """One entry of `data/manifest.json`."""

    document_id: str
    path: str
    type: DocType
    title: str
    date: date
    customer_ids: list[str] = []
    references: list[str] = []
    ingested_at: date | None = None
    occurred_at: date | None = None
    # Policies
    policy_family: str | None = None
    version: int | None = None
    status: Literal["active", "superseded", "draft"] | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    supersedes: str | None = None
    superseded_by: str | None = None
    applies_to_plans: list[str] | None = None
    key_terms: dict[str, Any] = {}
    # Contracts
    plan: str | None = None
    monthly_fee_usd: int | None = None
    pinned_policies: dict[str, PinnedPolicy] = {}
    exceptions: list[PolicyException] = []

    def in_force_on(self, day: date) -> bool:
        if self.status == "draft" or self.valid_from is None:
            return False
        return self.valid_from <= day and (self.valid_to is None or day <= self.valid_to)


class Manifest(BaseModel):
    dataset: str
    version: int
    documents: list[DocumentMeta]


class Document(BaseModel):
    meta: DocumentMeta
    text: str

    @property
    def id(self) -> str:
        return self.meta.document_id


# --- Domain rules (data/domain_rules.json) ----------------------------------------------------


class PolicyFamilyRules(BaseModel):
    clauses: dict[str, list[str]]  # clause name -> query keywords that make it relevant


class IntentRules(BaseModel):
    keywords: list[str]
    policy_family: str | None = None
    requires: list[Literal["incident", "contract", "applicable_policy"]] = []
    expansion_priority: list[DocType] = []


class DomainRules(BaseModel):
    policy_families: dict[str, PolicyFamilyRules]
    intents: dict[str, IntentRules]


# --- Retrieval --------------------------------------------------------------------------------


class Chunk(BaseModel):
    chunk_id: str
    document_id: str
    section: str | None
    text: str


class ScoredChunk(BaseModel):
    chunk: Chunk
    score: float
    rank: int  # 1-based
    source: str  # retriever name, or "rrf"


# --- Evidence package -------------------------------------------------------------------------


class ChunkRef(BaseModel):
    chunk_id: str
    section: str | None
    text: str
    source: str


class EvidenceItem(BaseModel):
    document_id: str
    title: str
    type: DocType
    chunks: list[ChunkRef]
    why_included: list[str]
    version_status: VersionStatus = "n/a"


class CandidateVersion(BaseModel):
    document_id: str
    valid_from: date | None
    valid_to: date | None
    relevant_terms: dict[str, Any]


class DateMention(BaseModel):
    day: date
    end: date | None = None  # set when only month/year was given
    source: Literal["question", "event", "agent_as_of"]
    detail: str = ""


class TemporalAssessment(BaseModel):
    policy_family: str
    dates_considered: list[DateMention]
    relevant_date: date | None
    date_source: Literal["event", "question", "agent_as_of", "none"]
    applicable: list[str]
    governed_by: GovernedBy
    justification: str
    ambiguity_detected: bool = False
    date_conflict: bool = False
    candidate_interpretations: list[CandidateVersion] = []
    clarification_needed: bool = False
    date_notes: list[str] = []


class Sufficiency(BaseModel):
    status: Literal["sufficient", "insufficient", "unknown"]
    missing: list[str] = []
    reason: str


class EvidencePackage(BaseModel):
    query: str
    as_of_date: date | None
    method: str
    intent: str | None
    evidence: list[EvidenceItem]
    temporal: list[TemporalAssessment] = []
    sufficiency: Sufficiency
    retrieved_ranking: list[str] = Field(description="Document IDs ranked by retrieval, before expansion")

    @property
    def ambiguity_detected(self) -> bool:
        return any(t.ambiguity_detected for t in self.temporal)

    @property
    def clarification_needed(self) -> bool:
        return any(t.clarification_needed for t in self.temporal)


# --- Evaluation -------------------------------------------------------------------------------


class ExpectedFlags(BaseModel):
    ambiguity_detected: bool = False
    clarification_needed: bool = False


class Question(BaseModel):
    id: str
    split: Literal["dev", "heldout"]
    category: str
    question: str
    answerable: bool
    gold_evidence: list[str]
    gold_version: dict[str, str] = {}
    expected_missing: list[str] = []
    expected_flags: ExpectedFlags = ExpectedFlags()
    expected_answer: str
    notes: str = ""
