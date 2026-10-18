# 22: Expose operational failures without logging private contents

Status: ready-for-agent
Approval: ticket breakdown approved by Sourav
Blocked by: 18, 20
Parent: [First-release specification](../spec.md)
Acceptance trace: AC-19, AC-20, AC-23
Worker routing: Budget worker candidate; stronger review required before completion.

## What to build

The app shows actionable unresolved failures and last-success information while operational logs remain safe.

## Acceptance criteria

- [ ] Processing, readiness, review, partial import and advice-unavailable states remain distinguishable and link to relevant problems.
- [ ] Show last successful processing and backup information (no backup success until a real generation exists); persist unresolved failures across restart.
- [ ] Capture only job IDs, timings, stages and sanitized errors; tests assert private statement text, descriptions, account identifiers and credentials are absent.
- [ ] No email/push alerts; ordinary committed use remains independent of laptop/NAS state.

## Test interface and verification

Application status/report interfaces and browser issue navigation. Use independently reviewed expected values and the approved
interfaces. For new behavioral code, observe a failing test and implement the minimum slice,
then repeat. Evaluation/evidence work runs the relevant existing checks; do not
create contrived tests of documentation. Include usable integration and meaningful
tests with the behavior rather than leaving a parser or UI stub. Follow [shared execution rules](../ticket-plan.md#execution-proposal)
for review, host evidence and permission limits.

## Prerequisites and scope limit

Independent sensitive sentinel fixture, not real private data in logs/tests.

Backup implementation supplies its success/failure events later; never manufacture success for this UI.

## Completion evidence

Not started. Record red/green commands, behavioral demo, review findings/fixes,
local versus actual-host results, unresolved limits and commit reference when
available. Passing local tests alone cannot close a required real-host gate.
