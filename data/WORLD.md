# Northstar Cloud — World Bible (ground truth)

This file is the single source of truth for the synthetic dataset. Every document in `data/` is
derived from it. It is written for humans (and for writing evaluation questions); the retrieval
system does **not** index this file.

All companies, people and numbers are fictional.

---

## 1. The company

**Northstar Cloud** sells a B2B SaaS platform, **Northstar Platform**, for API-based data
pipelines and workflow automation. Three plans:

| Plan | SLA service credits | Support |
|------|---------------------|---------|
| Starter | **Not eligible** for SLA credits | Email, next business day |
| Business | Eligible (standard SLA) | Email + chat, 8 business hours |
| Enterprise | Eligible (standard SLA, unless the contract says otherwise) | 24/7, 1-hour response for Sev-1 |

People (all fictional):

| Name | Role |
|------|------|
| Jonas Weber | CEO |
| Daniel Okafor | CTO |
| Mei Lin | VP Engineering |
| Sara Haddad | Head of Customer Success |
| Arjun Mehta | Security Lead |
| Hannah Brooks | Legal Counsel |
| Priya Raman | Account Manager (Acme Corp, Corvid Health) |
| Tomás Ortega | Account Manager (Acme Logistics, Delta Freight) |
| Lena Novak | Account Manager (Beta Ltd, Everfield Retail) |

---

## 2. Policies and their versions

### 2.1 Standard Service Level Agreement (family `service_sla`)

Credits are a percentage of the customer's **monthly fee** for the affected month and are based on
**monthly availability**. Applies to Business and Enterprise plans only.

| ID | Version | In force | Credit tiers | Claim process |
|----|---------|----------|--------------|---------------|
| SLA-001 | v1 | 2026-01-01 → 2026-06-30 | < 99.5% → 5%; < 99.0% → 10% | Applied automatically |
| SLA-002 | v2 | 2026-07-01 → 2026-09-30 | < 99.9% → 10%; < 99.5% → 20% | Applied automatically |
| SLA-003 | v3 | 2026-10-01 → (current) | < 99.9% → 15%; < 99.5% → 25% | Customer must request within **30 days after the end of the affected month** |

- SLA v2 was approved at the pricing & policy meeting of 2026-06-10 (MTG-001): moving the threshold to
  99.9% to stay competitive for enterprise deals.
- **DRF-001** is a *draft* SLA v3 (2026-09-10) proposing 20% / 30% credits and a 45-day claim window.
  It was **never adopted**. Leadership (MTG-004, 2026-09-20) approved the final SLA v3 (SLA-003) with
  15% / 25% and a 30-day window instead.

### 2.2 Refund policy (family `refund_policy`)

| ID | Version | In force | Monthly plans | Annual plans |
|----|---------|----------|---------------|--------------|
| REF-001 | v1 | 2026-01-01 → 2026-08-31 | Full refund within 30 days of first payment | Non-refundable |
| REF-002 | v2 | 2026-09-01 → (current) | Full refund within 30 days of first payment (unchanged) | Prorated refund if cancelled within the first 90 days |

Note: the **monthly** refund window is identical in both versions; only the annual rule changed.

### 2.3 Security policy (SEC-001, single version, in force since 2026-01-01)

- Customer data is encrypted at rest (AES-256) and in transit (TLS 1.2+).
- After contract termination, customer data is retained for **90 days**, then deleted.
- Customers are notified of a security incident affecting their data within **72 hours**.
- At the security review of 2026-07-30 (MTG-006) Arjun Mehta proposed reducing notification to 48
  hours. The proposal was **not approved** (deferred to the 2027 budget); 72 hours still applies.

### 2.4 Support policy (SUP-001, single version, in force since 2026-01-01)

Support tiers per plan (see table in §1). States explicitly that **Starter plans are excluded from
SLA service credits**.

---

## 3. Customers and contracts

| Customer | CRM ID | Plan | Monthly fee | Contract | Contract start | Special terms |
|----------|--------|------|-------------|----------|----------------|---------------|
| Acme Corp | CUS-001 | Enterprise | $12,000 | CTR-001 | 2026-03-01 | Standard SLA **as in force at the time of the incident** |
| Acme Logistics | CUS-002 | Business | $3,500 | CTR-002 | 2025-12-15 | **Pinned to SLA v1 (SLA-001)** for the whole initial term, until 2026-12-14 (grandfathered) |
| Beta Ltd | CUS-003 | Business | $4,000 | CTR-003 | 2026-05-01 | Includes a Salesforce CRM connector deliverable, originally due 2026-09-15 |
| Corvid Health | CUS-004 | Enterprise | $18,000 | CTR-004 | 2026-02-01 | **Exceptions:** flat 20% credit for any month below 99.9% (regardless of SLA version); security incident notification within **24 hours**; EU data residency |
| Delta Freight | CUS-005 | Starter | $400 | CTR-005 | 2026-06-01 | Starter → no SLA credits |
| Everfield Retail | CUS-006 | Business (proposed) | $3,000 (quoted) | **No signed contract** | — | Contract pending legal review as of 2026-10-05 |

"Acme Corp" and "Acme Logistics" are **unrelated companies** with similar names.

---

## 4. Incidents and tickets

Monthly availability is the figure for the whole affected month.

| Ticket | Date | Customer | What happened | Monthly availability | Correct outcome |
|--------|------|----------|---------------|---------------------|-----------------|
| INC-011 | 2026-04-18 | Acme Logistics | Regional network outage (eu-west) | April: 99.20% | Pinned SLA-001: < 99.5% → **5% of $3,500 = $175** |
| INC-012 | 2026-06-17 | Delta Freight | Scheduler crash, jobs not running | June: 98.90% | Starter plan → **no credit** |
| INC-013 | 2026-07-22 | Corvid Health | Storage latency degradation | July: 99.60% | Contract exception → **flat 20% of $18,000 = $3,600** (SLA-002 alone would give 10%) |
| INC-014 | 2026-08-21 | Acme Corp | Connection pool saturation on the primary Postgres cluster → elevated 5xx API error rates | August: 99.71% | SLA-002 in force → **10% of $12,000 = $1,200**, applied automatically |
| INC-015 | 2026-09-03 | Acme Logistics | Webhook delivery delays | September: 99.70% | Pinned SLA-001 (threshold 99.5%) → **no credit** (SLA-002 would have given 10%) |
| INC-016 | 2026-10-12 | Acme Corp | Full API outage after a failed deployment, ~4 hours | October: 99.42% | SLA-003 in force → < 99.5% → **25% of $12,000 = $3,000**, must be requested by **2026-11-30** |
| INC-017 | 2026-10-28 | Everfield Retail | Dashboard unavailable | October: 99.80% | **Cannot be determined**: no signed contract, plan and SLA eligibility unconfirmed |
| INC-018 | 2026-09-15 | Beta Ltd | *Service request*, not an outage: Beta asks for the status of the Salesforce connector | — | Connector postponed (see MTG-003); new target Q1 2027 |

---

## 5. Meetings and decisions

| ID | Date | Meeting | Key content |
|----|------|---------|-------------|
| MTG-001 | 2026-06-10 | Pricing & policy | Approves SLA v2 (99.9% threshold) from 2026-07-01 |
| MTG-006 | 2026-07-30 | Security review | Proposal to move incident notification from 72h to 48h → **not approved**, deferred to 2027 budget |
| MTG-002 | 2026-08-25 | Postmortem of INC-014 | Root cause: connection pool too small after a traffic increase; actions: raise pool size, add circuit breaker, write runbook (ENG-001) |
| MTG-003 | 2026-09-02 | Product planning | **Beta Ltd's Salesforce connector pushed to Q1 2027.** Two reasons: (1) engineering capacity moved to reliability work after INC-014; (2) Salesforce is retiring the API version the connector was built on, so it must be re-targeted. Lena Novak to inform Beta Ltd. |
| MTG-004 | 2026-09-20 | Leadership | Approves final SLA v3 (15% / 25%, 30-day claim window) from 2026-10-01; rejects the more generous draft DRF-001 as too costly |
| MTG-005 | 2026-10-05 | Customer success sync | Corvid Health renewal on track; Everfield Retail contract still in legal review (Hannah Brooks) |

---

## 6. Other documents

- **MKT-001**: public "Reliability Commitment" marketing page: "we target 99.99% uptime". Not contractual;
  contains no credit percentages.
- **ENG-001**: engineering runbook "Tuning Postgres connection pools" (2026-08-28), written after INC-014.

---

## 7. Things the dataset deliberately does NOT contain

Useful for *unanswerable* questions:
- Any revenue, profit, or total financial loss figure for Northstar Cloud.
- Any information about on-premise deployments (Northstar is cloud-only; on-prem is never mentioned).
- A signed contract for Everfield Retail.
- The names of Salesforce-side contacts or the exact new connector release date (only "Q1 2027").
- Credits actually *paid* in invoices (only what the policies/contracts entitle customers to).

---

## 8. Traps built in (for evaluation design)

| Trap | Where |
|------|-------|
| Similar customer names | Acme Corp vs Acme Logistics |
| Newer version is not the applicable one | INC-014 (Aug) → SLA-002, not SLA-003 |
| Contract pin overrides the version in force | Acme Logistics → SLA-001 even in September |
| Contract exception overrides any version | Corvid Health → flat 20% |
| Draft that was never adopted | DRF-001 vs SLA-003 |
| Proposal that was rejected | MTG-006 (48h) vs SEC-001 (72h) |
| Plan excludes the benefit | Delta Freight (Starter) |
| Missing piece of evidence | Everfield (no contract) |
| Paraphrase / different terminology | "outage" vs "elevated 5xx error rates", "delayed" vs "pushed to Q1 2027" |
| Temporally ambiguous, answer changes | "credit for 99.7% availability" (none / 10% / 15% depending on version) |
| Temporally ambiguous, answer does not change | "refund window for monthly plans" (30 days in both versions) |
| Marketing vs contractual | MKT-001 (99.99% target) vs SLA documents |
