# 26: Measure and meet dashboard and search latency

Status: ready-for-agent
Approval: ticket breakdown approved by Sourav
Blocked by: 06, 12, 13
Parent: [First-release specification](../spec.md)
Acceptance trace: AC-27
Worker routing: Budget worker candidate; stronger review required before completion.

## What to build

On the actual mini-PC, representative dashboard and text-search interactions meet the agreed measurable latency gate.

## Acceptance criteria

- [ ] Prepare an independently seeded 100,000-transaction dataset over up to ten years, with one active user and recorded query/range conditions.
- [ ] Measure at least 30 repetitions per representative journey after warm-up, submission to visible usable result; p95 at most two seconds over home LAN.
- [ ] Report cold load separately and distinguish Mac/VPN/transfer/inference timings from this gate.
- [ ] Make only measured corrections needed to meet the gate, keeping financial behavior/tests green; retain reproducible measurement instructions.

## Test interface and verification

Application/browser performance journeys on actual host. Use independently reviewed expected values and the approved
interfaces. For new behavioral code, observe a failing test and implement the minimum slice,
then repeat. Evaluation/evidence work runs the relevant existing checks; do not
create contrived tests of documentation. Include usable integration and meaningful
tests with the behavior rather than leaving a parser or UI stub. Follow [shared execution rules](../ticket-plan.md#execution-proposal)
for review, host evidence and permission limits.

## Prerequisites and scope limit

Authorized isolated actual-host workload and pinned browser/network/runtime conditions.

Do not introduce a search service or speculative optimization. Escalate unexpected shared-data/schema changes for stronger review.

## Completion evidence

Not started. Record red/green commands, behavioral demo, review findings/fixes,
local versus actual-host results, unresolved limits and commit reference when
available. Passing local tests alone cannot close a required real-host gate.
