# 25: Restore originals records and corrections into isolation

Status: ready-for-agent
Approval: ticket breakdown approved by Sourav
Blocked by: 24
Parent: [First-release specification](../spec.md)
Acceptance trace: AC-22
Worker routing: Stronger implementation/design oversight and independent review recommended.

## What to build

A successful recovery generation restores into an isolated target with working source links and retained user corrections.

## Acceptance criteria

- [ ] Restore independently from a completed recovery set into separate test data/storage, never over existing deployment data.
- [ ] Verify originals, transaction evidence, corrections, job/review state and reporting through normal application interfaces.
- [ ] Detect incomplete/unusable recovery input rather than claiming success; document the recovery procedure and loss since last successful generation.
- [ ] Record actual-host restore evidence and limits; no restart/restore test is presented as a physical power-loss guarantee.

## Test interface and verification

Infrastructure restore command and restored application public interfaces. Use independently reviewed expected values and the approved
interfaces. For new behavioral code, observe a failing test and implement the minimum slice,
then repeat. Evaluation/evidence work runs the relevant existing checks; do not
create contrived tests of documentation. Include usable integration and meaningful
tests with the behavior rather than leaving a parser or UI stub. Follow [shared execution rules](../ticket-plan.md#execution-proposal)
for review, host evidence and permission limits.

## Prerequisites and scope limit

P-07 isolated restore target and approval for actual-host recovery testing.

No destructive cutover or migration of existing data.

## Completion evidence

Not started. Record red/green commands, behavioral demo, review findings/fixes,
local versus actual-host results, unresolved limits and commit reference when
available. Passing local tests alone cannot close a required real-host gate.
