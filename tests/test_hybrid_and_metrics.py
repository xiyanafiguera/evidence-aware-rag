from evidence_aware_rag.evaluation import expected_governed_by, is_complete, recall_at_k, reciprocal_rank
from evidence_aware_rag.models import Chunk, Question, ScoredChunk
from evidence_aware_rag.retrievers.hybrid import rrf_fuse


def ranking(*chunk_ids: str, source: str = "x") -> list[ScoredChunk]:
    return [
        ScoredChunk(chunk=Chunk(chunk_id=cid, document_id=cid.split("#")[0], section=None, text=""),
                    score=0.0, rank=rank, source=source)
        for rank, cid in enumerate(chunk_ids, start=1)
    ]


def test_rrf_rewards_agreement_between_rankings():
    fused = rrf_fuse([ranking("A#0", "B#0", "C#0"), ranking("B#0", "C#0", "A#0")], k=60)
    assert [s.chunk.chunk_id for s in fused][0] == "B#0"  # ranks 2 and 1 beat ranks 1 and 3


def test_rrf_uses_ranks_not_scores_and_breaks_ties_deterministically():
    fused = rrf_fuse([ranking("B#0"), ranking("A#0")], k=60)
    assert [s.chunk.chunk_id for s in fused] == ["A#0", "B#0"]
    assert [s.rank for s in fused] == [1, 2]
    assert fused[0].score == 1 / 61


def test_recall_rr_and_completeness():
    ranked = ["X", "A", "Y", "B"]
    assert recall_at_k(ranked, ["A", "B"], 3) == 0.5
    assert recall_at_k(ranked, [], 3) is None
    assert reciprocal_rank(ranked, ["B", "A"]) == 0.5
    assert reciprocal_rank(ranked, ["Z"]) == 0.0
    assert is_complete(ranked, ["A", "B"]) is True
    assert is_complete(ranked[:2], ["A", "B"]) is False


def question(**overrides) -> Question:
    base = dict(id="T", split="dev", category="c", question="q", answerable=True,
                gold_evidence=[], gold_version={}, expected_answer="a")
    return Question(**(base | overrides))


def test_expected_governed_by_distinguishes_exception_pin_and_validity(corpus):
    exception = question(gold_evidence=["INC-013", "CTR-004"], gold_version={"service_sla": "CTR-004"})
    pin = question(gold_evidence=["INC-015", "CTR-002", "SLA-001"], gold_version={"service_sla": "SLA-001"})
    in_force = question(gold_evidence=["INC-014", "CTR-001", "SLA-002"], gold_version={"service_sla": "SLA-002"})
    assert expected_governed_by(exception, "service_sla", corpus) == "contract_exception"
    assert expected_governed_by(pin, "service_sla", corpus) == "contract_pin"
    assert expected_governed_by(in_force, "service_sla", corpus) == "in_force"
