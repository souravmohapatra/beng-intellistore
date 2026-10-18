# 12: Show dated balances and gap-aware period history

Status: ready-for-agent
Approval: ticket breakdown approved by Sourav
Blocked by: 11
Parent: [First-release specification](../spec.md)
Acceptance trace: AC-11, AC-24
Worker routing: Budget worker candidate; stronger review required before completion.

## What to build

A user selects month/year/custom periods and sees dated account balances and net-cash history without fabricated continuity.

## Acceptance criteria

- [ ] Retain twelve-month default; selected period consistently updates all figures and graph bounds.
- [ ] Show named-account current/savings balances and card debt with dates, provisional/coverage indicators and source context.
- [ ] Sparse savings observations and missing intervals appear as points/gaps rather than verified daily history.
- [ ] Older imported history stays queryable; changing period never deletes data.

## Test interface and verification

Reporting/application interfaces and browser period/chart journey. Use independently reviewed expected values and the approved
interfaces. For new behavioral code, observe a failing test and implement the minimum slice,
then repeat. Evaluation/evidence work runs the relevant existing checks; do not
create contrived tests of documentation. Include usable integration and meaningful
tests with the behavior rather than leaving a parser or UI stub. Follow [shared execution rules](../ticket-plan.md#execution-proposal)
for review, host evidence and permission limits.

## Prerequisites and scope limit

Independent sparse-history and historical-period fixtures.

No new chart library or FX portfolio conversion.

## Completion evidence

Not started. Record red/green commands, behavioral demo, review findings/fixes,
local versus actual-host results, unresolved limits and commit reference when
available. Passing local tests alone cannot close a required real-host gate.
