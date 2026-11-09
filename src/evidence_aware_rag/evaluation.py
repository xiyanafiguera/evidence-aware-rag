"""Evaluation: pure metric functions plus a runner that scores a pipeline on a question set.

Two things are measured separately, because the `full` mode returns more documents than the
others (relation expansion):

* **Ranking**: the retrieved list *before* expansion, same k for every mode (Recall@k, MRR).
* **Package**: the final EvidencePackage (completeness, version selection, flags, abstention),
  reported together with the average package size.
"""

from __future__ import annotations

from collections import defaultdict
from statistics import mean

from pydantic import BaseModel

from evidence_aware_rag.corpus import Corpus
from evidence_aware_rag.models import EvidencePackage, Question

# --- Metric functions -------------------------------------------------------------------------


def recall_at_k(ranked: list[str], gold: list[str], k: int) -> float | None:
    if not gold:
        return None
    return len(set(ranked[:k]) & set(gold)) / len(gold)


def reciprocal_rank(ranked: list[str], gold: list[str]) -> float | None:
    if not gold:
        return None
    for position, doc_id in enumerate(ranked, start=1):
        if doc_id in gold:
            return 1.0 / position
    return 0.0


def is_complete(found: list[str], gold: list[str]) -> bool | None:
    return set(gold) <= set(found) if gold else None


def expected_governed_by(question: Question, family: str, corpus: Corpus) -> str:
    """Why the gold version applies: a contract exception, a contract pin, or plain validity."""
    gold_id = question.gold_version[family]
    if corpus.meta(gold_id).type == "contract":
        return "contract_exception"
    for doc_id in question.gold_evidence:
        pin = corpus.meta(doc_id).pinned_policies.get(family) if doc_id in corpus else None
        if pin and pin.document_id == gold_id:
            return "contract_pin"
    return "in_force"


def version_correct(package: EvidencePackage, question: Question, corpus: Corpus) -> bool | None:
    """Correct only if the right document is selected *and* for the right reason."""
    if not question.gold_version:
        return None
    for family, gold_id in question.gold_version.items():
        assessment = next((t for t in package.temporal if t.policy_family == family), None)
        if assessment is None or assessment.applicable != [gold_id]:
            return False
        if assessment.governed_by != expected_governed_by(question, family, corpus):
            return False
    return True


# --- Runner -----------------------------------------------------------------------------------


class QuestionResult(BaseModel):
    id: str
    category: str
    answerable: bool
    ranking: list[str]
    package: list[str]
    recall_at_3: float | None
    recall_at_5: float | None
    rr: float | None
    complete_ranking_at_5: bool | None
    complete_package: bool | None
    version_ok: bool | None
    flags_ok: bool
    expected_ambiguity: bool
    detected_ambiguity: bool
    expected_clarification: bool
    detected_clarification: bool
    sufficiency: str
    missing: list[str]


def score_question(package: EvidencePackage, question: Question, corpus: Corpus) -> QuestionResult:
    gold = question.gold_evidence
    ranking = package.retrieved_ranking
    found = [item.document_id for item in package.evidence]
    flags = question.expected_flags
    return QuestionResult(
        id=question.id,
        category=question.category,
        answerable=question.answerable,
        ranking=ranking,
        package=found,
        recall_at_3=recall_at_k(ranking, gold, 3),
        recall_at_5=recall_at_k(ranking, gold, 5),
        rr=reciprocal_rank(ranking, gold),
        complete_ranking_at_5=is_complete(ranking[:5], gold),
        complete_package=is_complete(found, gold),
        version_ok=version_correct(package, question, corpus) if package.method == "full" else None,
        flags_ok=(package.ambiguity_detected == flags.ambiguity_detected
                  and package.clarification_needed == flags.clarification_needed),
        expected_ambiguity=flags.ambiguity_detected,
        detected_ambiguity=package.ambiguity_detected,
        expected_clarification=flags.clarification_needed,
        detected_clarification=package.clarification_needed,
        sufficiency=package.sufficiency.status,
        missing=package.sufficiency.missing,
    )


def _count(values: list[bool | None]) -> tuple[int, int]:
    scored = [v for v in values if v is not None]
    return sum(scored), len(scored)


def _avg(values: list[float | None]) -> float | None:
    scored = [v for v in values if v is not None]
    return round(mean(scored), 3) if scored else None


def summarize(results: list[QuestionResult]) -> dict:
    answerable = [r for r in results if r.answerable]
    unanswerable = [r for r in results if not r.answerable]
    ambiguous = [r for r in results if r.expected_ambiguity]
    return {
        "questions": len(results),
        "recall_at_3": _avg([r.recall_at_3 for r in results]),
        "recall_at_5": _avg([r.recall_at_5 for r in results]),
        "mrr": _avg([r.rr for r in results]),
        "complete_ranking_at_5": _count([r.complete_ranking_at_5 for r in results]),
        "complete_package": _count([r.complete_package for r in results]),
        "avg_package_size": round(mean(len(r.package) for r in results), 2) if results else 0,
        "version_correct": _count([r.version_ok for r in results]),
        "flags_correct": _count([r.flags_ok for r in results]),
        "ambiguity_detected_on_ambiguous": _count([r.detected_ambiguity for r in ambiguous]),
        "unanswerable": {
            "insufficient": sum(r.sufficiency == "insufficient" for r in unanswerable),
            "unknown": sum(r.sufficiency == "unknown" for r in unanswerable),
            "sufficient": sum(r.sufficiency == "sufficient" for r in unanswerable),
            "total": len(unanswerable),
        },
        "false_insufficient_on_answerable": sum(r.sufficiency == "insufficient" for r in answerable),
    }


def summarize_by_category(results: list[QuestionResult]) -> dict[str, dict]:
    groups: dict[str, list[QuestionResult]] = defaultdict(list)
    for r in results:
        groups[r.category].append(r)
    return {category: summarize(group) for category, group in sorted(groups.items())}
