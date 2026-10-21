# 12: Show dated balances and gap-aware period history

Status: done
Approval: ticket breakdown approved by Sourav
Blocked by: 11
Parent: [First-release specification](../spec.md)
Acceptance trace: AC-11, AC-24
Worker routing: Budget worker candidate; stronger review required before completion.

## What to build

A user selects month/year/custom periods and sees dated account balances and net-cash history without fabricated continuity.

## Acceptance criteria

- [x] Retain twelve-month default; selected period consistently updates all figures and graph bounds.
- [x] Show named-account current/savings balances and card debt with dates, provisional/coverage indicators and source context.
- [x] Sparse savings observations and missing intervals appear as points/gaps rather than verified daily history.
- [x] Older imported history stays queryable; changing period never deletes data.

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

Period selection: `?month=YYYY-MM`, `?year=YYYY` and `?start=&end=` all drive the
same totals, bounds, balance table and history; the default remains the trailing
twelve months (leap-day safe). An invalid or reversed range falls back to the
default with a visible message instead of an error. Older imports remain
queryable with a custom range.

Balances: the overview lists every named account with its latest dated balance,
kind, date and source filename, or `no balance evidence`. Card debt is shown as
debt and subtracted in net cash. Conflicting observations for the same account
on the latest date are marked Disputed with a count of alternatives, excluded
from net cash, and flagged in an alert — never silently resolved by newest row.

History and gaps: `reporting/history.py` builds points only for dates with
balance evidence, computing each point from the latest observation at or before
that date; no daily continuity is implied. Intervals longer than 45 days between
observations (including period edges) are listed as coverage gaps. Sparse
savings evidence therefore appears as isolated points.

Green: `.venv/bin/python manage.py test --noinput` → 134 tests OK;
`./scripts/smoke.sh` → exit 0, 134 tests, `restart check ok`.

Live demo: `?month=2026-08` showed the 1–31 August bounds, period totals, the
provisional and incomplete-balance alerts, the account balance table with dated
sources, and exactly two net-cash points (1 Aug and 31 Aug) rather than a daily
series.

Limits: history renders as dated points/list, not a chart, until the responsive/
visual slice; the 45-day gap threshold is a display heuristic awaiting review
workflow; conflicting sources need a resolution action (ticket 14). No
deployment or push. Record red/green commands, behavioral demo, review findings/fixes,
local versus actual-host results, unresolved limits and commit reference when
available. Passing local tests alone cannot close a required real-host gate.
