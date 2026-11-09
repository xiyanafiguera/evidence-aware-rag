# Results — heldout split

Commit `a3ce18a` · 2026-11-09 17:24 UTC · 8 questions

## Ranking (retrieved list before expansion, same k for all modes)

| Mode | Recall@3 | Recall@5 | MRR | All gold docs in top-5 |
|------|----------|----------|-----|------------------------|
| bm25 | 0.77 | 0.77 | 0.92 | 4/8 |
| dense | 0.67 | 0.77 | 0.84 | 4/8 |
| hybrid | 0.71 | 0.83 | 0.92 | 5/8 |
| full | 0.67 | 0.83 | 0.78 | 5/8 |

## Evidence package

| Mode | All gold docs in package | Avg package size | Correct version + reason | Ambiguity flags correct | Unanswerable → insufficient / unknown / sufficient | False 'insufficient' on answerable |
|------|---|---|---|---|---|---|
| bm25 | 4/8 | 5 | — | 7/8 | 0 / 1 / 0 (of 1) | 0 |
| dense | 4/8 | 5 | — | 7/8 | 0 / 1 / 0 (of 1) | 0 |
| hybrid | 5/8 | 5 | — | 7/8 | 0 / 1 / 0 (of 1) | 0 |
| full | 8/8 | 9.62 | 3/6 | 6/8 | 0 / 0 / 1 (of 1) | 0 |

## By category (all gold docs in top-5 ranking / in package)

| Category | bm25 | dense | hybrid | full |
|---|---|---|---|---|
| lexical | 1/1 / 1/1 | 1/1 / 1/1 | 1/1 / 1/1 | 1/1 / 1/1 |
| multi_hop | 0/1 / 0/1 | 0/1 / 0/1 | 0/1 / 0/1 | 0/1 / 1/1 |
| multi_hop_temporal | 1/2 / 1/2 | 0/2 / 0/2 | 1/2 / 1/2 | 1/2 / 2/2 |
| semantic | 0/1 / 0/1 | 1/1 / 1/1 | 1/1 / 1/1 | 1/1 / 1/1 |
| temporal | 1/1 / 1/1 | 1/1 / 1/1 | 1/1 / 1/1 | 1/1 / 1/1 |
| temporal_ambiguous | 1/1 / 1/1 | 1/1 / 1/1 | 1/1 / 1/1 | 1/1 / 1/1 |
| unanswerable | 0/1 / 0/1 | 0/1 / 0/1 | 0/1 / 0/1 | 0/1 / 1/1 |

## Per question

| ID | Category | bm25: ranking top-5 | dense: ranking top-5 | hybrid: ranking top-5 | full: ranking top-5 |
|---|---|---|---|---|---|
| H01 | lexical | INC-011, MTG-005, MTG-001, MTG-002, DRF-001 | INC-011, INC-016, INC-012, INC-014, INC-017 | INC-011, INC-017, INC-016, INC-012, INC-018 | INC-011, INC-017, INC-016, INC-012, INC-018 |
| H02 | semantic | MKT-001, MTG-001, DRF-001, MTG-006, SLA-002 | MKT-001, SLA-001, MTG-005, SLA-003, MTG-001 | MKT-001, SLA-001, MTG-001, SLA-002, SLA-003 | MKT-001, SLA-001, MTG-001, SLA-002, SLA-003 |
| H03 | multi_hop_temporal | SLA-003, MTG-002, INC-016, SLA-001, CUS-001 | SLA-003, INC-016, MTG-002, INC-015, CTR-002 | SLA-003, INC-016, MTG-002, SLA-001, CUS-001 | CUS-001, SLA-003, INC-016, MTG-002, SLA-001 |
| H04 | multi_hop_temporal | CTR-004, MTG-006, SEC-001, CUS-004, MTG-003 | CTR-004, MTG-006, CUS-004, INC-013, MTG-005 | CTR-004, MTG-006, CUS-004, SEC-001, INC-013 | CUS-004, CTR-004, MTG-006, SEC-001, INC-013 |
| H05 | temporal | REF-002, REF-001, SEC-001, SLA-003, DRF-001 | REF-001, REF-002, MTG-005, CTR-004, CTR-003 | REF-002, REF-001, SLA-003, MTG-005, SEC-001 | REF-002, REF-001, SLA-003, MTG-005, SEC-001 |
| H06 | temporal_ambiguous | REF-002, REF-001, MTG-003, MTG-001, CUS-001 | REF-002, REF-001, MTG-005, SLA-003, SUP-001 | REF-002, REF-001, CTR-003, CTR-004, MTG-003 | REF-002, REF-001, CTR-003, CTR-004, MTG-003 |
| H07 | unanswerable | MTG-002, INC-016, CTR-001, CUS-001, DRF-001 | MTG-002, INC-016, MTG-005, CTR-001, INC-015 | MTG-002, INC-016, CTR-001, MTG-005, CUS-001 | CUS-001, MTG-002, INC-016, CTR-001, MTG-005 |
| H08 | multi_hop | DRF-001, MTG-004, REF-002, REF-001, MKT-001 | DRF-001, MTG-004, REF-002, REF-001, MTG-006 | DRF-001, MTG-004, REF-002, MTG-005, MTG-003 | DRF-001, MTG-004, REF-002, MTG-005, MTG-003 |

Counts are absolute (hits/total). The dataset is small and synthetic: these numbers describe this prototype, they are not a benchmark.
