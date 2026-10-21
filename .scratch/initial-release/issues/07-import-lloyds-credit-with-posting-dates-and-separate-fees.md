# 07: Import Lloyds Credit with posting dates and separate fees

Status: done
Approval: ticket breakdown approved by Sourav
Blocked by: 05
Parent: [First-release specification](../spec.md)
Acceptance trace: AC-05, AC-08
Worker routing: Budget worker candidate; stronger review required before completion.

## What to build

A Lloyds Credit upload shows billed purchases, payment credits, fees and debt evidence in the same transaction/evidence flow.

## Acceptance criteria

- [x] Independent synthetic fixtures cover date entered versus purchase date, omitted years, attached CR markers, continuation rows and repeated headers.
- [x] Billed GBP values and standalone non-sterling fees reconcile with statement debit/credit/debt summaries; foreign amounts are annotations.
- [x] Payment due information is not an executed payment; preserve the actual payment credit and source locator.
- [x] Invalid source arithmetic or ambiguous year context creates a visible review failure without guessed financial publication.

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

Layout evidence: the supplied Lloyds Credit statement was re-read locally
(read-only, amounts masked) to record structure only: cover statement date,
``Previous balance``/``Payments received``/``New balance``, table rows of
``card · transaction date · date entered · description · amount[CR]`` with the
year omitted, foreign-currency continuation lines, standalone
``NON-STERLING PURCHASE FEE`` rows and repeated table headers. Fixture amounts,
descriptions and dates are unrelated synthetic values chosen and reconciled
independently; an earlier draft accidentally reused summary amounts seen during
inspection and was replaced before commit (`git grep` confirms none remain).

Interpretation: `interpretation/lloyds_credit.py` derives the omitted year from
the statement date (month after the statement month rolls back a year), reports
`missing_statement_date`/`ambiguous_transaction_year` instead of guessing,
attaches `CR` as a debt-reducing credit, ignores FX continuation lines as
annotations, treats fee rows as real debits, and reconciles previous balance +
debits − credits against the new balance and stated payments.

Distinct dates: `Transaction.source_transaction_date` retains the purchase date;
`posted_on` is the date entered.

Publication: `lloyds_credit` sections are mapped to card accounts; card
sections validate the debt equation and stated credit/debit totals because the
source supplies no per-row running balance. A credit statement assigned to a
current account requests review and imports nothing. Payment-due text never
creates a transaction.

Green: `.venv/bin/python manage.py test` → 75 tests OK; `./scripts/smoke.sh` →
exit 0, 75 tests, `restart check ok`.

Live demo: uploaded the synthetic credit statement to Lloyds Credit, released it
and ran the worker (`outcome: imported`); the account page shows seven debt
movements with posting and purchase dates, the £400 payment credit, the £0.75
fee, opening/closing debt and source page links.

Limits: one card layout; no FX ledger (annotations only); review still pending
on this slice before it is treated as final; real-source accuracy remains a
release gate. No deployment or push. Record red/green commands, behavioral demo, review findings/fixes,
local versus actual-host results, unresolved limits and commit reference when
available. Passing local tests alone cannot close a required real-host gate.
