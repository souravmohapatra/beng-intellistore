# 21: Integrate bounded laptop wake and keep-awake leases

Status: ready-for-agent
Approval: ticket breakdown approved by Sourav
Blocked by: 20
Parent: [First-release specification](../spec.md)
Acceptance trace: AC-18
Worker routing: Stronger implementation/design oversight and independent review recommended.

## What to build

Eligible work wakes the laptop through the existing controller and maintains only its own bounded active-work inhibition.

## Acceptance criteria

- [ ] Prepare authenticated controller integration without leaking tokens; obtain approval before live power/lease testing.
- [ ] Verify actual sleep-to-wake/readiness and create/extend/release/expiry paths, including failure/crash and the eight-hour creation-based ceiling.
- [ ] Renew only legitimate active work, distinguish sleep lease from job ownership, and avoid accumulating excessive expiry through additive extensions.
- [ ] Release only application leases, never user leases or forced sleep; record actual-host evidence and retain local failure-contract tests.

## Test interface and verification

Infrastructure adapters plus actual controller/worker milestone. Use independently reviewed expected values and the approved
interfaces. For new behavioral code, observe a failing test and implement the minimum slice,
then repeat. Evaluation/evidence work runs the relevant existing checks; do not
create contrived tests of documentation. Include usable integration and meaningful
tests with the behavior rather than leaving a parser or UI stub. Follow [shared execution rules](../ticket-plan.md#execution-proposal)
for review, host evidence and permission limits.

## Prerequisites and scope limit

P-05 controller machine authentication; P-06 cap-aware timing; live integration approval.

No new controller service if the existing actions suffice; no uncontrolled sleep or power-loss test.

## Completion evidence

Not started. Record red/green commands, behavioral demo, review findings/fixes,
local versus actual-host results, unresolved limits and commit reference when
available. Passing local tests alone cannot close a required real-host gate.
