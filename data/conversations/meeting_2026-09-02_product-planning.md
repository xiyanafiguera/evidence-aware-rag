# Meeting notes — Product Planning (Q4)

Document ID: MTG-003
Date: September 2, 2026
Attendees: Daniel Okafor, Mei Lin, Sara Haddad, Lena Novak

## Reliability work

After the August incident (INC-014), Mei proposed dedicating two engineers for the rest of the
quarter to database reliability: per-tenant limits, circuit breaker, load testing. Approved.

## Salesforce connector for Beta Ltd

The connector was planned for September 15. Two problems:

1. The two engineers assigned to it are the ones moving to the reliability work.
2. Salesforce announced the retirement of the API version the prototype was built on, so the
   connector would need to be re-targeted to the newer API anyway.

**Decision:** push the connector to Q1 2027 and build it directly on the new Salesforce API. Lena
will inform Beta Ltd and agree the new date in writing, as their contract requires.

## Other

- Dashboard redesign stays on track for November.
