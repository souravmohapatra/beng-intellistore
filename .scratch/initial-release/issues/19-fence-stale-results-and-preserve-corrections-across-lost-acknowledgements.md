# 19: Fence stale results and preserve corrections across lost acknowledgements

Status: ready-for-agent
Approval: ticket breakdown approved by Sourav
Blocked by: 14, 18
Parent: [First-release specification](../spec.md)
Acceptance trace: AC-06, AC-13, AC-16, AC-17
Worker routing: Stronger implementation/design oversight and independent review recommended.

## What to build

Results can be safely resubmitted after lost acknowledgements and cannot replace newer attempts or confirmed edits.

## Acceptance criteria

- [ ] A committed result whose acknowledgement is lost returns prior success on identical resubmission without duplicate effects.
- [ ] Conflicting content under the same attempt identity is rejected; expired/stale attempts cannot publish over newer ownership/results.
- [ ] A correction saved during processing remains authoritative and contradictory output is flagged.
- [ ] If new transaction identities cannot safely attach confirmed corrections, retain the previous published view and request review; observe through public interfaces.

## Test interface and verification

Application result/review/report interfaces with actual transactions and coordinated concurrent submissions. Use independently reviewed expected values and the approved
interfaces. For new behavioral code, observe a failing test and implement the minimum slice,
then repeat. Evaluation/evidence work runs the relevant existing checks; do not
create contrived tests of documentation. Include usable integration and meaningful
tests with the behavior rather than leaving a parser or UI stub. Follow [shared execution rules](../ticket-plan.md#execution-proposal)
for review, host evidence and permission limits.

## Prerequisites and scope limit

P-02 publication/fencing contract and independently scheduled race scenarios.

No claim of exactly-once computation or direct DB assertions as a substitute for observable correctness.

## Completion evidence

Not started. Record red/green commands, behavioral demo, review findings/fixes,
local versus actual-host results, unresolved limits and commit reference when
available. Passing local tests alone cannot close a required real-host gate.
