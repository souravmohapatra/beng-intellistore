# 14: Review and reverse a correction without losing history

Status: ready-for-agent
Approval: ticket breakdown approved by Sourav
Blocked by: 11
Parent: [First-release specification](../spec.md)
Acceptance trace: AC-13
Worker routing: Stronger implementation/design oversight and independent review recommended.

## What to build

A user resolves one issue beside source evidence and sees the effect of an explicit correction, with a validated history-preserving revert.

## Acceptance criteria

- [ ] Show source page/row, extracted value, proposed edit/match and before/after effect; require explicit save/confirm/reject.
- [ ] Keep extracted values separate from confirmed overrides and update affected committed reporting consistently.
- [ ] Reverting restores the source-derived value through validation and retains correction history; no silent deletion of evidence.
- [ ] Create a concurrent-edit/reprocessing acceptance case for later adversarial publication verification; unconfirmed suggestions have no effects.

## Test interface and verification

Application review/report interfaces and browser review journey. Use independently reviewed expected values and the approved
interfaces. For new behavioral code, observe a failing test and implement the minimum slice,
then repeat. Evaluation/evidence work runs the relevant existing checks; do not
create contrived tests of documentation. Include usable integration and meaningful
tests with the behavior rather than leaving a parser or UI stub. Follow [shared execution rules](../ticket-plan.md#execution-proposal)
for review, host evidence and permission limits.

## Prerequisites and scope limit

P-02 correction ownership/history contract; independent correction/revert examples.

No bulk approval or rule-learning engine.

## Completion evidence

Not started. Record red/green commands, behavioral demo, review findings/fixes,
local versus actual-host results, unresolved limits and commit reference when
available. Passing local tests alone cannot close a required real-host gate.
