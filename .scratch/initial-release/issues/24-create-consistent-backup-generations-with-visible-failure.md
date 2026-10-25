# 24: Create consistent backup generations with visible failure

> Superseded execution task; not closed as complete. Status below is historical. Remaining work is owned by the [authoritative backlog](../../product-completion/ticket-plan.md).

Status: ready-for-agent
Approval: ticket breakdown approved by Sourav
Blocked by: 14
Parent: [First-release specification](../spec.md)
Acceptance trace: AC-19, AC-21, AC-23
Worker routing: Stronger implementation/design oversight and independent review recommended.

## What to build

A 03:00 Europe/London backup produces a consistent original-plus-record recovery set and exposes its outcome without blocking normal use.

## Acceptance criteria

- [ ] Specify a consistent committed-state backup method that includes associated originals/corrections while processing continues.
- [ ] Only fully completed generations count; retain seven successes and retire oldest only after a new success.
- [ ] Interrupted copies, full/unavailable target and schedule/DST/catch-up failures remain visible and cannot delete local data or good recovery sets.
- [ ] Prove failure/retention behavior locally with isolated storage, then verify the user-approved NAS destination; no NAS project compute.

## Test interface and verification

Infrastructure backup command and application backup-status interface with isolated targets, then NAS milestone. Use independently reviewed expected values and the approved
interfaces. For new behavioral code, observe a failing test and implement the minimum slice,
then repeat. Evaluation/evidence work runs the relevant existing checks; do not
create contrived tests of documentation. Include usable integration and meaningful
tests with the behavior rather than leaving a parser or UI stub. Follow [shared execution rules](../ticket-plan.md#execution-proposal)
for review, host evidence and permission limits.

## Prerequisites and scope limit

P-04 destination path/headroom; P-07 consistency/retirement contract and live target approval.

No elaborate/off-site backups; never copy a live database directory without a valid consistency mechanism.

## Completion evidence

Not started. Record red/green commands, behavioral demo, review findings/fixes,
local versus actual-host results, unresolved limits and commit reference when
available. Passing local tests alone cannot close a required real-host gate.
