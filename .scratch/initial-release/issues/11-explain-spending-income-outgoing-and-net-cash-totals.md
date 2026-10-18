# 11: Explain spending income outgoing and net cash totals

Status: ready-for-agent
Approval: ticket breakdown approved by Sourav
Blocked by: 05
Parent: [First-release specification](../spec.md)
Acceptance trace: AC-08, AC-11
Worker routing: Budget worker candidate; stronger review required before completion.

## What to build

The dashboard shows independently verifiable posting-period totals with explicit provisional classifications rather than simply adding source totals.

## Acceptance criteria

- [ ] Use independent literal examples for purchases, identified salary/interest, card liabilities and current-account outgoing; no floating-point money.
- [ ] Net cash combines tracked current/debit/savings balances less card debt while preserving currency and evidence limitations.
- [ ] Unknown amount/currency is excluded from affected totals; unresolved classification/matching is visible and does not become invented confirmed income.
- [ ] Keep classification rules separate from the LLM and expose enough reporting detail for later drill-down and review slices.

## Test interface and verification

Public reporting and application report/browser summary interfaces. Use independently reviewed expected values and the approved
interfaces. For new behavioral code, observe a failing test and implement the minimum slice,
then repeat. Evaluation/evidence work runs the relevant existing checks; do not
create contrived tests of documentation. Include usable integration and meaningful
tests with the behavior rather than leaving a parser or UI stub. Follow [shared execution rules](../ticket-plan.md#execution-proposal)
for review, host evidence and permission limits.

## Prerequisites and scope limit

Normalized public reporting inputs from initial import contract; independent financial examples.

Do not add heuristic transfer matching or charts. Strong financial review of literal expected results is required.

## Completion evidence

Not started. Record red/green commands, behavioral demo, review findings/fixes,
local versus actual-host results, unresolved limits and commit reference when
available. Passing local tests alone cannot close a required real-host gate.
