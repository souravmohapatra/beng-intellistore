# 05: Import Lloyds Current into a source-linked transaction view

Status: ready-for-agent
Approval: ticket breakdown approved by Sourav
Blocked by: 04
Parent: [First-release specification](../spec.md)
Acceptance trace: AC-05, AC-17
Worker routing: Budget worker candidate; stronger review required before completion.

## What to build

A Lloyds Current upload is processed by the worker and appears as exact, dated transactions and balance observations with original evidence.

## Acceptance criteria

- [ ] Build a synthetic layout fixture and independent expected rows before implementing extraction; handle interleaved accessibility text and continuation headers.
- [ ] Normalize money-in/out to exact pence, preserve source descriptions/types/date meanings and locators, and reconcile running/summary balances.
- [ ] A failed reconciliation retains the original and prior financial view with a review issue; no guessed rows.
- [ ] Demonstrate upload, Process now, assigned-source processing, committed transaction list and source reopening end to end on the Mac.

## Test interface and verification

Statement interpretation/reporting, application worker/result interfaces and browser transaction view. Use independently reviewed expected values and the approved
interfaces. For new behavioral code, observe a failing test and implement the minimum slice,
then repeat. Evaluation/evidence work runs the relevant existing checks; do not
create contrived tests of documentation. Include usable integration and meaningful
tests with the behavior rather than leaving a parser or UI stub. Follow [shared execution rules](../ticket-plan.md#execution-proposal)
for review, host evidence and permission limits.

## Prerequisites and scope limit

P-03 Lloyds Current fixture/oracle; public interpretation interface established by this slice.

One supplied statement layout only. Strong review of initial parser/publication contract is mandatory.

## Completion evidence

Not started. Record red/green commands, behavioral demo, review findings/fixes,
local versus actual-host results, unresolved limits and commit reference when
available. Passing local tests alone cannot close a required real-host gate.
