# 30: Record release evidence and a reviewable milestone handoff

Status: ready-for-agent
Approval: ticket breakdown approved by Sourav
Blocked by: 29
Parent: [First-release specification](../spec.md)
Acceptance trace: AC-01, AC-02, AC-03, AC-04, AC-05, AC-06, AC-07, AC-08, AC-09, AC-10, AC-11, AC-12, AC-13, AC-14, AC-15, AC-16, AC-17, AC-18, AC-19, AC-20, AC-21, AC-22, AC-23, AC-24, AC-25, AC-26, AC-27
Worker routing: Stronger implementation/design oversight and independent review recommended.

## What to build

Sourav can review exactly which release requirements passed, what remains disabled and the verified operate/recover procedure.

## Acceptance criteria

- [ ] Map every AC and prerequisite to concrete evidence or an explicit unresolved/disabled capability; all core gates must pass before deployed-release claims.
- [ ] Record deterministic release status, advice disabled or passing evaluation/enabled status, actual performance and recovery limitations.
- [ ] Provide reproducible local/host verification, start/restart, backup/restore and rollback guidance tied to the tested state.
- [ ] Review final changes against spec and project standards; make coherent local commits as authorized, excluding local agent memory and private data.
- [ ] Present completed milestone and request explicit push approval separately; never treat release evidence as push or destructive migration approval.

## Test interface and verification

Release evidence against public acceptance interfaces and runnable documented commands. Use independently reviewed expected values and the approved
interfaces. For new behavioral code, observe a failing test and implement the minimum slice,
then repeat. Evaluation/evidence work runs the relevant existing checks; do not
create contrived tests of documentation. Include usable integration and meaningful
tests with the behavior rather than leaving a parser or UI stub. Follow [shared execution rules](../ticket-plan.md#execution-proposal)
for review, host evidence and permission limits.

## Prerequisites and scope limit

All core acceptance evidence; advice tickets only if enabling that optional capability.

Do not mark the spec done while required core gates remain unverified. No forced push or automatic deployment from ticket completion.

## Completion evidence

Not started. Record red/green commands, behavioral demo, review findings/fixes,
local versus actual-host results, unresolved limits and commit reference when
available. Passing local tests alone cannot close a required real-host gate.
