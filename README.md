# evidence-aware-rag

**Knowledge retrieval for AI agents that returns evidence, not just text chunks.** For a question
such as *"Is Acme Logistics owed a credit for the September webhook delays?"*, the system returns the
documents that answer it, **which policy version governs and why** (in force on the incident date,
pinned by the customer's contract, or overridden by a contract exception), whether the question is
**temporally ambiguous**, and whether the evidence is **structurally sufficient**. Everything is
exposed to agents through **MCP** and measured with a reproducible evaluation.

All data is synthetic: a fictional B2B SaaS company, *Northstar Cloud*, with 35 documents
(versioned policies, contracts, tickets, CRM records, meeting notes) built to contain the traps real
enterprise knowledge has.

> **Status:** retrieval, evidence packaging, MCP tools and evaluation are implemented and tested.
> There is **no LLM answer generation and no hosted demo yet**; both are listed under
> [Future work](#future-work).

---

## What it does

| Problem in enterprise knowledge | How this prototype handles it |
|---|---|
| Exact identifiers (`INC-014`) and paraphrases ("requests failing" vs "5xx error rates") | Hybrid retrieval: BM25 with an ID-preserving tokenizer + BGE embeddings, fused with Reciprocal Rank Fusion; exact ID/entity matching |
| The answer is spread across documents (ticket → contract → policy) | Deterministic expansion over explicit references (max 2 hops, capped, prioritized by intent), each document records *why* it was added |
| Several versions of a policy; the newest is not always the right one | `TemporalResolver`: contract exception > plan not covered > contract pin > version in force on the relevant date; drafts never apply |
| No date in the question | Returns all candidate versions and flags `clarification_needed` only if they differ on the clauses the question is about |
| Agents answering without the evidence they need | Structural sufficiency check (`sufficient` / `insufficient` / `unknown`) with the missing pieces named |

## Quickstart

Requires [uv](https://docs.astral.sh/uv/). Everything runs on CPU; the embedding model (~130 MB) is
downloaded once.

```bash
uv sync
uv run scripts/build_index.py       # chunk + embed the 35 documents (skipped if unchanged)
uv run scripts/evaluate.py          # dev split, all four modes → results/RESULTS_dev.md
```

Ask a question and see the evidence package:

```bash
uv run scripts/ask.py "What compensation is Acme Corp entitled to for INC-014?"
```

```
[service_sla] in_force: SLA-002
    SLA-002 in force on 2026-08-21 (INC-014 occurred_at) (valid 2026-07-01 → 2026-09-30)

sufficiency: sufficient
    compensation for CUS-001: found incident INC-014; contract CTR-001; service_sla: SLA-002 (in_force)

evidence:
  SLA-002 [applicable] Service Level Agreement v2
      · governing document (in_force): SLA-002 in force on 2026-08-21 ...
  CUS-001 CRM — Acme Corp
      · retrieved: exact+bm25+dense rank 1
  INC-014 Elevated 5xx API error rates
  ...
```

Run the tests (70, including MCP integration tests over stdio):

```bash
uv run pytest
```

## Use it from an agent (MCP)

```bash
claude mcp add evidence-aware-rag -- uv --directory /path/to/evidence-aware-rag run python -m evidence_aware_rag.mcp_server
```

| Tool | Returns |
|---|---|
| `search_knowledge(query, as_of_date?, max_documents=8)` | The evidence package (documents + matching chunks + provenance, temporal assessment, sufficiency) |
| `get_document(document_id)` | Full text and metadata |
| `list_sources(type?)` | What the knowledge base contains |
| `get_applicable_policy(policy_family, on_date, customer_id?)` | Which version governs, and why |

All tools are read-only. `as_of_date` is the date the question is asked; it never silently overrides
a date the question refers to (an incident date, "in May 2026"), and any difference is reported.

**[→ A recorded session](docs/example_agent_session.md)** of Claude Code answering a question through
these tools, avoiding the trap where the SLA in force would wrongly grant a credit.

## Architecture

```
query ─► QueryAnalyzer (IDs, customers, dates, intent)
      ─► Retrieval: RRF( Exact, BM25, Dense )            ← modes bm25 / dense / hybrid stop here
      ─► RelationExpander (references, ≤ 2 hops, ≤ 8 docs, why_included)
      ─► TemporalResolver (exception > not covered > pin > in force; ambiguity)
      ─► SufficiencyChecker (required pieces per intent)
      ─► EvidencePackage ─► MCP server · evaluation · CLI
```

```
src/evidence_aware_rag/
├── config.py          settings (all tunable numbers, pinned model revision)
├── models.py          pydantic models: manifest, EvidencePackage, questions
├── corpus.py          loads manifest + documents, metadata lookups
├── chunking.py        section-level chunks, prefixed with the document title
├── retrievers/        bm25.py · dense.py · exact.py · hybrid.py (RRF)
├── index_store.py     fingerprinted index (rebuilt only when chunks or model change)
├── query_analysis.py  rule-based signals from the query
├── relations.py       reference expansion with provenance
├── temporal.py        version selection, date roles, ambiguity
├── sufficiency.py     structural sufficiency
├── pipeline.py        the four evaluation modes
├── evaluation.py      metric functions
└── mcp_server.py      MCP tools (mcp 2.x MCPServer)
```

Domain knowledge (which clauses a policy has, which keywords signal them, what a compensation
question requires) lives in [`data/domain_rules.json`](data/domain_rules.json), not in the code.

## Evaluation

Two question sets: **dev** (17 questions, used during development) and **held-out** (8 questions,
written by a different author from the world description only, without seeing the documents or the
code, and evaluated **once**, on commit `a3ce18a`, after the configuration was frozen). No parameter
was tuned: the configuration in `config.py` is the initial one. Categories: single-document,
lexical, semantic, multi-hop, temporal, temporally ambiguous, unanswerable.

Two kinds of measures, because `full` returns more documents than the other modes:

- **Ranking**: the retrieved list before expansion, same k = 5 for every mode.
- **Evidence package**: the final package, reported together with its size.

### Results (counts are absolute)

| Mode | All gold docs in top-5 ranking | MRR | All gold docs in package (avg size) | Correct version **and** reason | Ambiguity flags correct | Unanswerable → `insufficient` / `unknown` / `sufficient` |
|---|---|---|---|---|---|---|
| **dev** · bm25 | 9/16 | 0.68 | 9/16 (4.8) | — | 15/17 | 0 / 2 / 0 |
| **dev** · dense | 10/16 | 0.74 | 10/16 (5.0) | — | 15/17 | 0 / 2 / 0 |
| **dev** · hybrid | 12/16 | 0.82 | 12/16 (5.0) | — | 15/17 | 0 / 2 / 0 |
| **dev** · full | 12/16 | 0.66 | **16/16** (9.1) | **5/5** | **17/17** | 1 / 1 / 0 |
| **held-out** · bm25 | 4/8 | 0.92 | 4/8 (5.0) | — | 7/8 | 0 / 1 / 0 |
| **held-out** · dense | 4/8 | 0.84 | 4/8 (5.0) | — | 7/8 | 0 / 1 / 0 |
| **held-out** · hybrid | 5/8 | 0.92 | 5/8 (5.0) | — | 7/8 | 0 / 1 / 0 |
| **held-out** · full | 5/8 | 0.78 | **8/8** (9.6) | **3/6** | 6/8 | 0 / 0 / **1** ✗ |

*Complete evidence retrieval does not imply correct policy interpretation or answerability; these are
evaluated separately.*

Full tables (per category, per question): [`results/RESULTS_dev.md`](results/RESULTS_dev.md),
[`results/RESULTS_heldout.md`](results/RESULTS_heldout.md).

**How to read this honestly**

- Hybrid beats BM25 and Dense alone on ranking in both splits. Relation expansion is what gets every
  gold document into the package (16/16, 8/8), at the cost of a package about twice as large.
- `full` has a *lower* MRR: exact matching puts the named customer's CRM record at rank 1, and that
  record is rarely the gold evidence.
- The baselines' "ambiguity flags correct" is trivially high: they never flag anything, and most
  questions are not ambiguous.
- With 8–17 questions, one question moves a metric by 6–12 points. This is a prototype on synthetic
  data, not a benchmark.

### Held-out failures (analysed after the single run, not fixed and re-run)

| Question (abridged) | What went wrong | Root cause |
|---|---|---|
| H02 "...the commitment customers can claim credits against **today**?" | Flagged as ambiguous instead of selecting SLA-003 | Relative dates ("today", "currently") are not interpreted, and the evaluation passes no `as_of_date` |
| H08 "a **September** proposal... the **October** policy rollout" | Ambiguous instead of SLA-003 | Month names **without a year** are ignored by the date parser |
| H07 "Did Finance actually post Acme Corp's **August** credit to its invoice?" | Marked `sufficient`, and selected the October version | (1) Structural sufficiency checks the pieces of the *entitlement* (incident, contract, SLA), not the information actually asked (invoice records). (2) "August" without a year is ignored, so the first Acme incident retrieved (October, the one that says "outage") was taken as the event |

H07 shows the main limitation of rule-based sufficiency: it can prove that required evidence is
*missing*, but it cannot prove that the retrieved evidence *answers the question that was asked*.

## Design choices (what this is and is not)

- **Relation expansion is graph traversal over explicit references**, not learned multi-hop reasoning.
  It is deterministic, auditable and cheap; a knowledge graph is the natural next step.
- **RRF scores are rankings, never confidences.** No threshold on retrieval scores is used to decide
  sufficiency.
- **Sufficiency is structural and conservative.** Only intents with declared requirements can be
  `sufficient` or `insufficient`; everything else is `unknown`, reported separately.
- **Intent detection and clause relevance are hand-written rules** in `domain_rules.json`. This is
  stated plainly: they make every decision traceable, and they are also where the system is most
  brittle (see H07).
- **Reproducibility:** exact FAISS search, deterministic tie-breaking, pinned model revision, and an
  index that is rebuilt only when its fingerprint changes. The held-out run is guarded by the script:
  it refuses a dirty tree or an existing result.

## Limitations

- Small synthetic corpus; questions written by the same team that designed the world (mitigated by a
  blind held-out set).
- Relative dates and month names without a year are not resolved (H02, H08).
- Event selection takes the first-ranked ticket of the customer; it does not use cited months to
  choose between incidents (H07).
- Sufficiency cannot judge whether the evidence answers the specific question (H07).
- No answer generation yet: the output is the evidence package.

## Future work

1. **Clarification strategy for agents** (designed, not implemented). The package already exposes
   `ambiguity_detected`, `candidate_interpretations` and `clarification_needed`. Proposed decision rule
   for an agent:
   - *Answer directly* when the candidate interpretations give the same answer (e.g. the monthly
     refund window is 30 days in both refund-policy versions).
   - *Answer under a stated assumption* when they differ but context resolves it (an `as_of_date`, a
     customer whose contract pins a version), and say which assumption was made.
   - *Ask* when they differ, nothing in the context resolves them, and the answer has consequences
     (money, legal commitments). Example: *"What credit does the SLA give at 99.7% availability?"* →
     none (v1), 10% (v2) or 15% (v3, current) → *"Do you mean the current SLA, or a specific month?"*
   - Longer term: decide between asking, retrieving more evidence or answering by weighing the cost of
     a wrong answer against the cost of another step.
2. **Answer generation** with citations and abstention, through an OpenAI-compatible endpoint (e.g. a
   serverless GPU running Qwen3-4B-Instruct), evaluated on citation validity and abstention. This is
   also where answerability (H07) belongs.
3. Relative-date and year-less month resolution; cited months used to choose the event.
4. A knowledge graph in place of manifest references; a reranker; larger and more varied corpora.

## Repository layout

```
data/       35 documents, manifest.json (versions, validity, references), domain_rules.json, WORLD.md (ground truth)
eval/       questions_dev.json, questions_heldout.json
results/    measured results (generated by scripts/evaluate.py)
scripts/    validate_data.py · build_index.py · evaluate.py · ask.py
docs/       example_agent_session.md
tests/      pytest suite
```

`uv run scripts/validate_data.py` checks that the manifest, documents, rules and questions are
consistent (schemas, references, non-overlapping validity periods).

## How this was built

Developed with AI coding agents under a structured workflow (written plans reviewed before each
phase, session continuity, tests at every step); the commit history shows the order in which it was
built.
