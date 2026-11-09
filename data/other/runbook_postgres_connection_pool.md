# Runbook — Tuning Postgres connection pools

Document ID: ENG-001
Created: August 28, 2026 (after INC-014)
Owner: Mei Lin

## Symptoms

- API latency rises, then requests fail with 503 "upstream unavailable".
- Pool metrics show `waiting_clients > 0` for more than one minute.

## Safe procedure

1. Check current usage: `SHOW POOLS;` on the pooler.
2. Increase `default_pool_size` in steps of 20, never above the database `max_connections` minus 15%.
3. Reload the pooler (no restart needed).
4. Confirm `waiting_clients` returns to 0 within five minutes.

## Prevention

- Per-tenant connection limits so one customer cannot exhaust the pool.
- Alert when pool utilisation exceeds 80% for ten minutes.
