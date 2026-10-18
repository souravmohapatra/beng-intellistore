# 13: Search descriptions and drill into metric evidence

Status: ready-for-agent
Approval: ticket breakdown approved by Sourav
Blocked by: 11
Parent: [First-release specification](../spec.md)
Acceptance trace: AC-01, AC-12
Worker routing: Budget worker candidate; stronger review required before completion.

## What to build

A user opens contributing transactions from a metric or searches original descriptions and reaches supporting originals with period context intact.

## Acceptance criteria

- [ ] Search matches original name/description text, not model-normalized merchant guesses.
- [ ] Metric drill-down explains included/excluded/provisional rows and retains selected reporting period.
- [ ] Every result reaches authenticated supporting source evidence; unauthorized access remains denied.
- [ ] Results remain usable for a large result set without requiring all records in one browser view.

## Test interface and verification

Application search/report interfaces and browser drill-down journey. Use independently reviewed expected values and the approved
interfaces. For new behavioral code, observe a failing test and implement the minimum slice,
then repeat. Evaluation/evidence work runs the relevant existing checks; do not
create contrived tests of documentation. Include usable integration and meaningful
tests with the behavior rather than leaving a parser or UI stub. Follow [shared execution rules](../ticket-plan.md#execution-proposal)
for review, host evidence and permission limits.

## Prerequisites and scope limit

Independent search strings and literal expected result sets.

No conversational/semantic search or unsolicited advanced filtering.

## Completion evidence

Not started. Record red/green commands, behavioral demo, review findings/fixes,
local versus actual-host results, unresolved limits and commit reference when
available. Passing local tests alone cannot close a required real-host gate.
