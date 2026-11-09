# Results — dev split

Commit `ed6897d` · 2026-11-09 17:14 UTC · 17 questions

## Ranking (retrieved list before expansion, same k for all modes)

| Mode | Recall@3 | Recall@5 | MRR | All gold docs in top-5 |
|------|----------|----------|-----|------------------------|
| bm25 | 0.66 | 0.75 | 0.68 | 9/16 |
| dense | 0.66 | 0.78 | 0.74 | 10/16 |
| hybrid | 0.71 | 0.86 | 0.82 | 12/16 |

## Evidence package

| Mode | All gold docs in package | Avg package size | Correct version + reason | Ambiguity flags correct | Unanswerable → insufficient / unknown / sufficient | False 'insufficient' on answerable |
|------|---|---|---|---|---|---|
| bm25 | 9/16 | 4.82 | — | 15/17 | 0 / 2 / 0 (of 2) | 0 |
| dense | 10/16 | 5 | — | 15/17 | 0 / 2 / 0 (of 2) | 0 |
| hybrid | 12/16 | 5 | — | 15/17 | 0 / 2 / 0 (of 2) | 0 |

## By category (all gold docs in top-5 ranking / in package)

| Category | bm25 | dense | hybrid |
|---|---|---|---|
| lexical | 2/2 / 2/2 | 1/2 / 1/2 | 2/2 / 2/2 |
| multi_hop | 0/1 / 0/1 | 1/1 / 1/1 | 1/1 / 1/1 |
| multi_hop_temporal | 1/3 / 1/3 | 1/3 / 1/3 | 1/3 / 1/3 |
| semantic | 1/3 / 1/3 | 2/3 / 2/3 | 3/3 / 3/3 |
| single_doc | 3/3 / 3/3 | 3/3 / 3/3 | 2/3 / 2/3 |
| temporal | 0/1 / 0/1 | 0/1 / 0/1 | 1/1 / 1/1 |
| temporal_ambiguous | 1/2 / 1/2 | 1/2 / 1/2 | 1/2 / 1/2 |
| unanswerable | 1/1 / 1/1 | 1/1 / 1/1 | 1/1 / 1/1 |

## Per question

| ID | Category | bm25: ranking top-5 | dense: ranking top-5 | hybrid: ranking top-5 |
|---|---|---|---|---|
| D01 | single_doc | SEC-001, CTR-003, CTR-004, CTR-001, REF-001 | SEC-001, CTR-003, SLA-001, SLA-003, SLA-002 | SEC-001, CTR-003, CTR-001, CTR-004, REF-001 |
| D02 | single_doc | SUP-001, CTR-002, CTR-005, CTR-003, CTR-001 | SUP-001, CTR-002, CTR-001, CTR-004, MTG-005 | SUP-001, CTR-002, CTR-001, CTR-005, CTR-004 |
| D03 | lexical | INC-012, SLA-001, SLA-002, SLA-003 | INC-016, INC-014, ENG-001, INC-011, INC-017 | INC-012, SLA-002, SLA-001, INC-016, INC-014 |
| D04 | lexical | ENG-001, MTG-002, MTG-001 | ENG-001, MTG-002, INC-014, INC-013, MTG-003 | ENG-001, MTG-002, MTG-001, INC-014, INC-013 |
| D05 | semantic | MTG-002, CTR-001, CUS-001, REF-001, REF-002 | MTG-002, INC-016, INC-014, CTR-001, INC-015 | MTG-002, CTR-001, CUS-001, INC-014, INC-016 |
| D06 | semantic | CTR-003, CUS-003, MTG-003, MTG-005, INC-018 | CTR-003, CUS-003, MTG-003, MTG-005, INC-018 | CTR-003, CUS-003, MTG-003, MTG-005, INC-018 |
| D07 | semantic | MTG-005, REF-002, DRF-001, SEC-001, REF-001 | SEC-001, SLA-002, CTR-003, SLA-001, SLA-003 | SEC-001, SLA-001, MTG-006, MKT-001, MTG-005 |
| D08 | multi_hop_temporal | MTG-002, CTR-001, INC-016, INC-012, INC-014 | CTR-001, CUS-001, INC-016, INC-014, MTG-002 | CTR-001, MTG-002, INC-016, CUS-001, INC-014 |
| D09 | multi_hop_temporal | INC-015, CTR-002, CUS-002, MTG-005, ENG-001 | INC-015, CTR-002, MTG-005, CUS-002, CTR-001 | INC-015, CTR-002, CUS-002, MTG-005, INC-011 |
| D10 | multi_hop_temporal | INC-013, CTR-004, MTG-005, CUS-004, SLA-002 | CTR-004, INC-013, MTG-005, CUS-004, DRF-001 | CTR-004, INC-013, MTG-005, CUS-004, SLA-001 |
| D11 | temporal | MTG-005, CTR-002, SUP-001, DRF-001, SLA-003 | DRF-001, MTG-001, MTG-005, MTG-004, SLA-003 | DRF-001, MTG-005, CTR-002, SLA-001, SLA-003 |
| D12 | temporal_ambiguous | DRF-001, SLA-001, CTR-002, SLA-002, SLA-003 | DRF-001, MTG-001, SLA-003, SLA-002, MTG-005 | DRF-001, SLA-001, SLA-003, SLA-002, CTR-002 |
| D13 | temporal_ambiguous | CTR-001, CTR-005, CTR-002, CTR-003, CTR-004 | REF-001, REF-002, MTG-005, SLA-003, DRF-001 | REF-001, MTG-005, CTR-003, DRF-001, CTR-004 |
| D14 | multi_hop | INC-012, CTR-005, CUS-005, MTG-002, INC-016 | INC-012, CTR-005, CUS-005, MTG-005, SUP-001 | INC-012, CTR-005, CUS-005, MTG-002, SUP-001 |
| D15 | unanswerable | INC-017, CUS-006, MTG-005, CTR-005, ENG-001 | INC-017, MTG-005, CUS-006, INC-018, DRF-001 | INC-017, CUS-006, MTG-005, DRF-001, CTR-005 |
| D16 | unanswerable | MTG-002, CTR-001, SLA-001, SLA-002, SLA-003 | SEC-001, SLA-003, CTR-001, INC-016, CTR-003 | CTR-001, SLA-003, SLA-001, SEC-001, CTR-003 |
| D17 | single_doc | DRF-001, SLA-002, SLA-003, SLA-001, MTG-001 | MTG-001, MTG-004, DRF-001, MTG-005, SLA-003 | DRF-001, MTG-001, MTG-004, SLA-001, SLA-002 |

Counts are absolute (hits/total). The dataset is small and synthetic: these numbers describe this prototype, they are not a benchmark.
