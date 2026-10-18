# 08: Import Amex without duplicating annual or FX totals

Status: ready-for-agent
Approval: ticket breakdown approved by Sourav
Blocked by: 05
Parent: [First-release specification](../spec.md)
Acceptance trace: AC-05, AC-08
Worker routing: Budget worker candidate; stronger review required before completion.

## What to build

An Amex upload shows exact billed rows and credits using process dates, with evidence linked through the existing flow.

## Acceptance criteria

- [ ] Synthetic fixtures cover transaction/process dates, multiline descriptions, following-line CR and statement-period/year context.
- [ ] Monthly billed rows reconcile with the summary; embedded FX fee disclosure is not added twice.
- [ ] Annual summary/terms pages do not become transactions; preserve source/page evidence and actual monthly coverage.
- [ ] Show source validation errors without replacing the previous financial view.

## Test interface and verification

Statement interpretation and application publication/browser transaction view. Use independently reviewed expected values and the approved
interfaces. For new behavioral code, observe a failing test and implement the minimum slice,
then repeat. Evaluation/evidence work runs the relevant existing checks; do not
create contrived tests of documentation. Include usable integration and meaningful
tests with the behavior rather than leaving a parser or UI stub. Follow [shared execution rules](../ticket-plan.md#execution-proposal)
for review, host evidence and permission limits.

## Prerequisites and scope limit

P-03 Amex fixtures and independent oracle.

No new categories or inference-assisted amount extraction.

## Completion evidence

Not started. Record red/green commands, behavioral demo, review findings/fixes,
local versus actual-host results, unresolved limits and commit reference when
available. Passing local tests alone cannot close a required real-host gate.
