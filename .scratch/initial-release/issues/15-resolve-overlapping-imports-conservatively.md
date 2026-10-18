# 15: Resolve overlapping imports conservatively

Status: ready-for-agent
Approval: ticket breakdown approved by Sourav
Blocked by: 14
Parent: [First-release specification](../spec.md)
Acceptance trace: AC-06, AC-07, AC-13
Worker routing: Stronger implementation/design oversight and independent review recommended.

## What to build

Repeated originals and overlapping sources avoid duplicate financial effects without collapsing genuine identical-looking transactions.

## Acceptance criteria

- [ ] Same bytes with consistent mapping produce one financial effect while keeping receipts/provenance; changed mapping cannot silently relocate records.
- [ ] Different originals merge logical records only with supported stable identity or unambiguous sequence/balance evidence validated by independent fixtures.
- [ ] Two identical date/amount/description purchases remain distinct without stronger proof; uncertain overlaps surface for review.
- [ ] A confirmed duplicate decision preserves both sources and survives reprocessing without losing confirmed corrections.

## Test interface and verification

Application import/review/report interfaces and statement overlap examples. Use independently reviewed expected values and the approved
interfaces. For new behavioral code, observe a failing test and implement the minimum slice,
then repeat. Evaluation/evidence work runs the relevant existing checks; do not
create contrived tests of documentation. Include usable integration and meaningful
tests with the behavior rather than leaving a parser or UI stub. Follow [shared execution rules](../ticket-plan.md#execution-proposal)
for review, host evidence and permission limits.

## Prerequisites and scope limit

P-03 independently reviewed overlap/year-boundary fixtures; additional private evidence if needed.

No fuzzy tuple-only auto-deduplication or invented source identifiers.

## Completion evidence

Not started. Record red/green commands, behavioral demo, review findings/fixes,
local versus actual-host results, unresolved limits and commit reference when
available. Passing local tests alone cannot close a required real-host gate.
