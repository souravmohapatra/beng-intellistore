# 27: Show validated optional advice without risking financial imports

> Superseded execution task; not closed as complete. Status below is historical. Remaining work is owned by the [authoritative backlog](../../product-completion/ticket-plan.md).

Status: ready-for-agent
Approval: ticket breakdown approved by Sourav
Blocked by: 14
Parent: [First-release specification](../spec.md)
Acceptance trace: AC-25
Worker routing: Budget worker candidate; stronger review required before completion.

## What to build

An unresolved review item can show a source-linked structured local classification suggestion, or remain usable when advice fails.

## Acceptance criteria

- [ ] Validate allowed classifications, source references, short explanation and abstention; malformed/missing-evidence output is rejected.
- [ ] No advice can alter amounts/dates/balances or bypass explicit confirmation; confirmed corrections remain authoritative.
- [ ] Timeout/unavailable advice does not fail/reimport deterministic financial facts; bound separate retries and show advice unavailable.
- [ ] Advice stays disabled for actual inference until the candidate-evaluation gate passes; no cloud fallback or raw financial logging.

## Test interface and verification

Application advisory/review/report interfaces and browser review with controlled external model adapter. Use independently reviewed expected values and the approved
interfaces. For new behavioral code, observe a failing test and implement the minimum slice,
then repeat. Evaluation/evidence work runs the relevant existing checks; do not
create contrived tests of documentation. Include usable integration and meaningful
tests with the behavior rather than leaving a parser or UI stub. Follow [shared execution rules](../ticket-plan.md#execution-proposal)
for review, host evidence and permission limits.

## Prerequisites and scope limit

Separate advisory contract; P-06 bounded advice timeout/retry choices.

Use controlled responses for local behavioral tests, not a downloaded model or unverified quality claims.

## Completion evidence

Not started. Record red/green commands, behavioral demo, review findings/fixes,
local versus actual-host results, unresolved limits and commit reference when
available. Passing local tests alone cannot close a required real-host gate.
