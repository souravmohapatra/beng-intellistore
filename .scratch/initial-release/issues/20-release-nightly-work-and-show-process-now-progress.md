# 20: Release nightly work and show Process now progress

Status: ready-for-agent
Approval: ticket breakdown approved by Sourav
Blocked by: 04
Parent: [First-release specification](../spec.md)
Acceptance trace: AC-14, AC-20
Worker routing: Budget worker candidate; stronger review required before completion.

## What to build

Uploads release at 21:00 Europe/London or Process now, with visible asynchronous status and safe restart catch-up.

## Acceptance criteria

- [ ] Pending work remains ineligible just because the laptop is awake; an empty due queue sends no wake request.
- [ ] Process now releases all waiting uploads without interrupting a job or duplicating work on repeat clicks.
- [ ] One catch-up after a missed schedule, including DST/restart cases, does not replay every missed day.
- [ ] Ten-minute wake-to-application-readiness deadline leaves unavailable work queued for manual retry/next batch; cached health/acknowledgement is not readiness.

## Test interface and verification

Application scheduling/job interfaces and browser status with controllable clock/controller. Use independently reviewed expected values and the approved
interfaces. For new behavioral code, observe a failing test and implement the minimum slice,
then repeat. Evaluation/evidence work runs the relevant existing checks; do not
create contrived tests of documentation. Include usable integration and meaningful
tests with the behavior rather than leaving a parser or UI stub. Follow [shared execution rules](../ticket-plan.md#execution-proposal)
for review, host evidence and permission limits.

## Prerequisites and scope limit

P-06 readiness probes and clock/timezone fixture contract.

Use controlled controller behavior locally; real wake/lease lifecycle belongs to the next slice.

## Completion evidence

Not started. Record red/green commands, behavioral demo, review findings/fixes,
local versus actual-host results, unresolved limits and commit reference when
available. Passing local tests alone cannot close a required real-host gate.
