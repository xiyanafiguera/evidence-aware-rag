# Example: an AI agent using the MCP server

A real, unedited session recorded on 2026-11-10: Claude Code running non-interactively
(`claude -p`, model `claude-opus-5-5`), with **only** this repository's MCP tools allowed. The agent
decided which tools to call and with which arguments.

```bash
claude -p "Acme Logistics is asking for a service credit for the webhook delays they had at the \
start of September 2026. Are they entitled to one? Use the knowledge base tools and cite document IDs." \
  --mcp-config mcp.json --strict-mcp-config \
  --allowedTools "mcp__evidence-aware-rag__search_knowledge,mcp__evidence-aware-rag__get_document,..."
```

Why this question is a trap: the SLA version **in force** in September 2026 is v2 (SLA-002), which
would grant a 10% credit at 99.7% availability. But Acme Logistics' contract (CTR-002) **pins** SLA v1
until 2026-12-14, and v1's threshold is 99.5%, so no credit is due.

## 1. Tool calls made by the agent

```json
search_knowledge {"query": "Acme Logistics service credit webhook delays early September 2026",
                  "as_of_date": "2026-11-10"}
get_document     {"document_id": "SLA-001"}
```

The agent passed today's date as `as_of_date`. The resolver kept the three dates apart and chose
the version from the **event** date, as designed (as of 2026-11-10 the pin also applies, so no
`date_notes` warning was needed).

## 2. What `search_knowledge` returned (abridged)

```json
{
  "intent": "compensation",
  "temporal": [{
    "policy_family": "service_sla",
    "dates_considered": [
      {"day": "2026-09-03", "source": "event", "detail": "INC-015 occurred_at"},
      {"day": "2026-09-01", "end": "2026-09-30", "source": "question", "detail": "September 2026"},
      {"day": "2026-11-10", "source": "agent_as_of", "detail": "as_of_date"}
    ],
    "relevant_date": "2026-09-03",
    "date_source": "event",
    "applicable": ["SLA-001"],
    "governed_by": "contract_pin",
    "justification": "CTR-002 pins SLA-001 until 2026-12-14; relevant date 2026-09-03 (INC-015 occurred_at)",
    "ambiguity_detected": false,
    "clarification_needed": false
  }],
  "sufficiency": {
    "status": "sufficient",
    "reason": "compensation for CUS-002: found incident INC-015; contract CTR-002; service_sla: SLA-001 (contract_pin)"
  },
  "evidence": [
    {"document_id": "SLA-001", "version_status": "applicable",
     "why_included": ["referenced_by CTR-002 (hop 1)", "governing document (contract_pin): ..."]},
    {"document_id": "CUS-002", "why_included": ["retrieved: exact+bm25+dense rank 1"]},
    {"document_id": "INC-015", "why_included": ["retrieved: exact+bm25+dense rank 2"]},
    {"document_id": "CTR-002", "why_included": ["retrieved: exact+bm25+dense rank 3"]},
    {"document_id": "MTG-005", "why_included": ["retrieved: exact+bm25+dense rank 4"]},
    {"document_id": "INC-011", "why_included": ["retrieved: exact+bm25+dense rank 5"]},
    {"document_id": "SLA-003", "version_status": "not_applicable", "why_included": ["referenced_by MTG-005 (hop 1)"]},
    {"document_id": "SLA-002", "version_status": "not_applicable", "why_included": ["referenced_by SLA-003 (hop 2)"]}
  ]
}
```

(Each evidence item also carries up to three matching chunks with their `chunk_id`, omitted here.)

## 3. The agent's final answer (verbatim)

> **No, Acme Logistics isn't entitled to a service credit for the September 2026 webhook delays.**
>
> **Why:**
>
> 1. **The incident:** INC-015 was a Sev-2 incident on 2026-09-03, resolved 2026-09-04. Outgoing webhooks to Acme were delayed by up to 90 minutes because a worker autoscaling misconfiguration caused a queue backlog. The ticket records Acme's credit request and gives **monthly availability for 2026-09 as 99.7%**.
>
> 2. **Which SLA applies:** Acme (CUS-002, Business plan, $3,500/month) has a grandfathered contract. CTR-002 §"Service levels — grandfathered terms" keeps **SLA-001** in force for the whole initial term, until 2026-12-14, even though newer SLA versions have been published. So SLA-001 governs September 2026, not SLA-002, the standard SLA in force at the time (valid 2026-07-01 to 2026-09-30).
>
> 3. **SLA-001 terms:** SLA-001 commits to **99.5%** monthly availability. Credits start only below that level: 5% of the monthly fee below 99.5%, and 10% below 99.0%. At 99.7%, September stayed above the commitment, so no credit is due. Also, SLA-001 measures availability for the "API and dashboard." Webhook latency doesn't clearly fall under that definition.
>
> **Something to be aware of:** Under the standard SLA-002, 99.7% would have earned a **10% credit ($350)**, because its commitment is 99.9%. If someone looks up "the SLA in force in September" without checking Acme's contract, they could wrongly approve that credit. Acme's contract pin means it doesn't apply.
>
> **Context for the reply to Acme:**
> - Acme's earlier outage, INC-011 (April 2026, 99.2%), *did* qualify for a 5% credit under SLA-001. SLA-001 applies credits automatically, so Acme may be expecting the same process here.
> - MTG-005 notes that Acme renews in December and that Tomás Ortega plans to propose moving them to the current SLA (SLA-003: 99.9% commitment, 15–25% credits). The account team could offer a goodwill gesture or raise the better SLA terms as part of that renewal. Nothing in the knowledge base requires either.
>
> **Sources:** INC-015, CTR-002, SLA-001, CUS-002, SLA-002, SLA-003, INC-011, MTG-005. The knowledge base marked this evidence as sufficient and found no ambiguity about which date or SLA applies.

4 turns, about USD 0.17. The question is a paraphrase of development question D09, so it is not part
of the held-out evaluation.
