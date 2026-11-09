# Postmortem — INC-014 (Acme Corp, August 21)

Document ID: MTG-002
Date: August 25, 2026
Attendees: Mei Lin, Daniel Okafor, Priya Raman, on-call engineers

## Summary

For about four and a half hours, API requests failed with 503 errors. Acme Corp was the most
affected customer because of its high request volume.

## Root cause

The primary Postgres cluster's connection pool had been sized for traffic levels from early 2026.
After Acme Corp's ERP integration went live, peak concurrency exceeded the pool limit and requests
queued until they timed out.

## What went well / badly

- Detection was fast (alert within 3 minutes).
- Mitigation was slow: nobody on call knew the safe procedure to resize the pool.

## Action items

- Raise the pool size and add per-tenant connection limits (Mei Lin).
- Add a circuit breaker in the API gateway (on-call team).
- Write a runbook for connection pool tuning (done: ENG-001).
- Priya to confirm with Acme Corp that the August credit is applied automatically on the next invoice.
