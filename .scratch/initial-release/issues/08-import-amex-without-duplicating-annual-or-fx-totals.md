# 08: Import Amex without duplicating annual or FX totals

Status: done
Approval: ticket breakdown approved by Sourav
Blocked by: 05
Parent: [First-release specification](../spec.md)
Acceptance trace: AC-05, AC-08
Worker routing: Budget worker candidate; stronger review required before completion.

## What to build

An Amex upload shows exact billed rows and credits using process dates, with evidence linked through the existing flow.

## Acceptance criteria

- [x] Synthetic fixtures cover transaction/process dates, multiline descriptions, following-line CR and statement-period/year context.
- [x] Monthly billed rows reconcile with the summary; embedded FX fee disclosure is not added twice.
- [x] Annual summary/terms pages do not become transactions; preserve source/page evidence and actual monthly coverage.
- [x] Show source validation errors without replacing the previous financial view.

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

Layout evidence: the supplied Amex statement was re-read locally (read-only,
amounts masked) and its positions recorded: one text fragment per field, with
date/description baselines differing from the amount baseline by under a point;
`CR` sits on the following line; foreign-spend/exchange-rate/fee fragments sit
below the row; page 7 is an annual summary with no date columns.

Fixture: `positioned_statement_pdf` emits tokens at explicit `(x, y)` positions;
rows reproduce the observed baseline jitter (amount 0.7pt below the
description), CR on its own baseline and an annual-summary page. All amounts and
merchant names are invented and independently reconciled (opening 300.00,
credits 100.00, debits 642.25, closing 842.25).

Interpretation: `interpretation/amex.py` takes per-page `(x, y, text)` tokens,
clusters into lines with a 3pt baseline tolerance, reads
`transaction month/day · process month/day · details · amount`, attaches a
following-line `CR` as a debt-reducing credit, ignores FX/exchange/fee fragments
and annual-summary lines, infers the omitted year from the statement date and
uses the process date as `posted_on` while retaining the transaction date.
`Payments and Credits` must equal the rows' credits.

Publication: `amex` maps to card accounts and requires the source summary and
anchors; a wrong account kind requests review and imports nothing.

Green: `.venv/bin/python manage.py test` → 88 tests OK; `./scripts/smoke.sh` →
exit 0, 88 tests, `restart check ok`.

Live demo: uploaded the synthetic Amex PDF to a named Amex card account,
released it, worker returned `imported`; the account page shows five debt
movements using process dates with transaction dates retained, the −£100.00
credit, the dated closing debt and an undated opening balance, with source page
links.

Limits: one Amex layout; annual summary content is ignored rather than
cross-checked; real-source accuracy remains a release gate; no FX ledger. No
deployment or push. Record red/green commands, behavioral demo, review findings/fixes,
local versus actual-host results, unresolved limits and commit reference when
available. Passing local tests alone cannot close a required real-host gate.
