# 01: Open a private local account overview

Status: ready-for-agent
Approval: ticket breakdown approved by Sourav
Blocked by: None
Parent: [First-release specification](../spec.md)
Acceptance trace: AC-01, AC-11
Worker routing: Stronger implementation/design oversight and independent review recommended.

## What to build

Sourav can sign in locally and see named account slots and an honest empty dashboard backed by real PostgreSQL.

## Acceptance criteria

- [ ] Select and document the Mac test runtime before PostgreSQL-dependent tests; pin the initial compatible application/runtime dependencies.
- [ ] Login gates the account overview; anonymous access is denied and no self-service registration exists.
- [ ] Named account types include current, card and savings; empty balances are unknown, not fabricated zero history.
- [ ] A fresh checkout can run the local smoke check with isolated storage; no existing host services or private data are touched.

## Test interface and verification

Application interfaces and browser journey. Use independently reviewed expected values and the approved
interfaces. For new behavioral code, observe a failing test and implement the minimum slice,
then repeat. Evaluation/evidence work runs the relevant existing checks; do not
create contrived tests of documentation. Include usable integration and meaningful
tests with the behavior rather than leaving a parser or UI stub. Follow [shared execution rules](../ticket-plan.md#execution-proposal)
for review, host evidence and permission limits.

## Prerequisites and scope limit

P-01, initial P-02; settle the local runtime choice explicitly before installation.

Do not build upload, worker, charts or production TLS yet. This foundation earns its scope through a running authenticated user journey.

## Completion evidence

Not started. Record red/green commands, behavioral demo, review findings/fixes,
local versus actual-host results, unresolved limits and commit reference when
available. Passing local tests alone cannot close a required real-host gate.
