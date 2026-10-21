# 15: Resolve overlapping imports conservatively

Status: done
Approval: ticket breakdown approved by Sourav
Blocked by: 14
Parent: [First-release specification](../spec.md)
Acceptance trace: AC-06, AC-07, AC-13
Worker routing: Stronger implementation/design oversight and independent review recommended.

## What to build

Repeated originals and overlapping sources avoid duplicate financial effects without collapsing genuine identical-looking transactions.

## Acceptance criteria

- [x] Same bytes with consistent mapping produce one financial effect while keeping receipts/provenance; changed mapping cannot silently relocate records.
- [x] Different originals merge logical records only with supported stable identity or unambiguous sequence/balance evidence validated by independent fixtures.
- [x] Two identical date/amount/description purchases remain distinct without stronger proof; uncertain overlaps surface for review.
- [x] A confirmed duplicate decision preserves both sources and survives reprocessing without losing confirmed corrections.

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

Identical originals: publication checks for an already-imported upload with the
same original SHA-256 and the same account mapping (primary and savings). A
match returns outcome `duplicate`, sets the receipt to “Duplicate (already
imported)” with an `already_imported` issue, and adds no financial effects; both
receipts and the preserved original remain. The same bytes mapped to a different
named account still import (intake already warns about the earlier mapping) and
are never silently relocated.

Different originals: rows from another original with the same account, posting
date, amount and description are flagged `needs_review` on both sides and the
period becomes provisional. Tuple equality is never treated as proof and no rows
are merged automatically — the approved evidence rule for merging is not enabled
(AC2 remains an explicit non-goal here without a validated identity/sequence
fixture).

Confirmed decisions: review shows possible overlaps with the other source
file/page/row. “Confirm this row duplicates that one” records a `DuplicateMatch`,
clears review on both rows and suppresses only that row's reporting effect while
retaining both sources and provenance. Decisions are canonical: a row already
confirmed as a duplicate cannot be a target, and the reciprocal confirmation is
rejected, so a cycle cannot erase every effect. “Keep both as distinct” clears
the review flag and counts both.

Within-original identical rows are never candidates (the comparison excludes the
same upload), so genuine identical-looking purchases stay distinct.

Green: `.venv/bin/python manage.py test --noinput` → 179 tests OK;
`./scripts/smoke.sh` → exit 0, 179 tests, `restart check ok`.

Live demo: re-uploaded the same Lloyds Current PDF for the same account; the
worker returned `duplicate` and the receipt showed “Duplicate (already
imported)” with the `already_imported` issue and the preserved original.

Limits: no automatic merging (awaiting a validated evidence rule with independent
fixtures); duplicate decisions do not yet survive a reprocessing path (ticket 19
owns adversarial publication and correction preservation). No deployment or
push. Record red/green commands, behavioral demo, review findings/fixes,
local versus actual-host results, unresolved limits and commit reference when
available. Passing local tests alone cannot close a required real-host gate.
