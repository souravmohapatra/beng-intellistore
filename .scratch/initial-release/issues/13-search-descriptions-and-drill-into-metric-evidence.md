# 13: Search descriptions and drill into metric evidence

> Historical completed work; not an active task. Preserve evidence below. Use the [authoritative backlog](../../product-completion/ticket-plan.md).

Status: done
Approval: ticket breakdown approved by Sourav
Blocked by: 11
Parent: [First-release specification](../spec.md)
Acceptance trace: AC-01, AC-12
Worker routing: Budget worker candidate; stronger review required before completion.

## What to build

A user opens contributing transactions from a metric or searches original descriptions and reaches supporting originals with period context intact.

## Acceptance criteria

- [x] Search matches original name/description text, not model-normalized merchant guesses.
- [x] Metric drill-down explains included/excluded/provisional rows and retains selected reporting period.
- [x] Every result reaches authenticated supporting source evidence; unauthorized access remains denied.
- [x] Results remain usable for a large result set without requiring all records in one browser view.

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

Search: `/search/?q=` matches the original transaction description only
(case-insensitive substring), optionally scoped by `start`/`end`; category and
transaction type are not searched. Results show date, account, original
description, normalized amount and a link to the authenticated original; 50 per
page with counts.

Drill-down: dashboard metric links open `/transactions/?metric=…` with the
selected period. Each row shows why it is included (card purchase increases
debt, refund reverses spending, withdrawal, conversion out/back, identified
income, cash leaving a current account), its contribution and a source link. The
page states how many rows were excluded for unresolved classification (totals
provisional) and how many do not contribute to the metric; totals equal the
reporting totals for the same period. An unknown metric returns 400; anonymous
access redirects to login.

Green: `.venv/bin/python manage.py test --noinput` → 156 tests OK;
`./scripts/smoke.sh` → exit 0, 156 tests, `restart check ok`.

Live demo: `?metric=spending&start=2026-08-01&end=2026-08-31` listed the
contributing rows with explanations, showed 3 unresolved classifications and 5
non-contributing rows, and totalled £2,301.20; searching `coffee` returned three
original descriptions across Lloyds Current, Lloyds Credit and Amex with source
links.

Limits: search is a substring scan (no index) — performance is ticket 26; page
size is fixed at 50; no advanced/semantic filters. No deployment or push. Record red/green commands, behavioral demo, review findings/fixes,
local versus actual-host results, unresolved limits and commit reference when
available. Passing local tests alone cannot close a required real-host gate.
