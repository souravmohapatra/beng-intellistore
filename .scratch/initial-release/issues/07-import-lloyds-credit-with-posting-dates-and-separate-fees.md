# 07: Import Lloyds Credit with posting dates and separate fees

Status: ready-for-agent
Approval: ticket breakdown approved by Sourav
Blocked by: 05
Parent: [First-release specification](../spec.md)
Acceptance trace: AC-05, AC-08
Worker routing: Budget worker candidate; stronger review required before completion.

## What to build

A Lloyds Credit upload shows billed purchases, payment credits, fees and debt evidence in the same transaction/evidence flow.

## Acceptance criteria

- [ ] Independent synthetic fixtures cover date entered versus purchase date, omitted years, attached CR markers, continuation rows and repeated headers.
- [ ] Billed GBP values and standalone non-sterling fees reconcile with statement debit/credit/debt summaries; foreign amounts are annotations.
- [ ] Payment due information is not an executed payment; preserve the actual payment credit and source locator.
- [ ] Invalid source arithmetic or ambiguous year context creates a visible review failure without guessed financial publication.

## Test interface and verification

Statement interpretation and application publication/browser transaction view. Use independently reviewed expected values and the approved
interfaces. For new behavioral code, observe a failing test and implement the minimum slice,
then repeat. Evaluation/evidence work runs the relevant existing checks; do not
create contrived tests of documentation. Include usable integration and meaningful
tests with the behavior rather than leaving a parser or UI stub. Follow [shared execution rules](../ticket-plan.md#execution-proposal)
for review, host evidence and permission limits.

## Prerequisites and scope limit

P-03 Lloyds Credit fixtures; reuse existing normalized result interface.

No generic parser redesign; reporting/matching rules remain in their own slices.

## Completion evidence

Not started. Record red/green commands, behavioral demo, review findings/fixes,
local versus actual-host results, unresolved limits and commit reference when
available. Passing local tests alone cannot close a required real-host gate.
