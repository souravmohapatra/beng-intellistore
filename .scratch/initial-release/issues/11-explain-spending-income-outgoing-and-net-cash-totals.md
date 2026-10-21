# 11: Explain spending income outgoing and net cash totals

Status: done
Approval: ticket breakdown approved by Sourav
Blocked by: 05
Parent: [First-release specification](../spec.md)
Acceptance trace: AC-08, AC-11
Worker routing: Budget worker candidate; stronger review required before completion.

## What to build

The dashboard shows independently verifiable posting-period totals with explicit provisional classifications rather than simply adding source totals.

## Acceptance criteria

- [x] Use independent literal examples for purchases, identified salary/interest, card liabilities and current-account outgoing; no floating-point money.
- [x] Net cash combines tracked current/debit/savings balances less card debt while preserving currency and evidence limitations.
- [x] Unknown amount/currency is excluded from affected totals; unresolved classification/matching is visible and does not become invented confirmed income.
- [x] Keep classification rules separate from the LLM and expose enough reporting detail for later drill-down and review slices.

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

Reporting: `reporting/totals.py` is a pure, model-free classification layer over
committed transactions. Evidence-bound rules: card purchases increase spending;
card credits count only as repayments (payment markers) or evidenced refunds,
otherwise they are unclassified; current-account spending types and cash
withdrawals add spending and cash outgoing; refunds reverse spending in their
posting period; salary/interest are income only when identified by type or an
explicit SALARY description; currency conversions count only with `Exchanged to`
evidence (out: spending + outgoing; back to GBP: spending reduction). Everything
else is unclassified, excluded from totals and marked provisional. Money is
integer pence throughout.

Net cash: latest dated balance per tracked account up to the period end — current
and savings added, card debt subtracted. A missing balance marks the position
incomplete and names the account; it is never treated as zero. Ignored Revolut
sections therefore cause no coverage error.

UI: the overview shows the trailing-twelve-month period, spending, income, cash
outgoing and net cash with separate provisional and incomplete-balance alerts;
an empty period says it has no evidence rather than showing zeros.

Red: `reporting` package absent (10 tests).

Green: `.venv/bin/python manage.py test --noinput` → 119 tests OK;
`./scripts/smoke.sh` → exit 0, 119 tests, `restart check ok`.

Independent literals: salary +250000, rent −95000, withdrawal −10000, refund
+1244, card purchase +5000 → spending 108756 pence, income 250010, outgoing
105000 (the card-side repayment credit carries no cash movement); net cash from
balances 300000 + 25030 − 2000 = 323030. Counterexamples assert that an
unidentified `Bank credit`, a card CR without repayment/refund evidence, and a
transfer to an excluded product stay unclassified rather than becoming income,
refunds or spending.

Live demo: the dashboard rendered the trailing-year period with spending,
income, outgoing and a negative net-cash position, plus `Provisional: 3
transaction(s)` and an incomplete-balance warning for an account without
evidence.

Limits: keywords are the only available classification evidence until the review
slice adds corrections; no transfer matching or charts here (tickets 13-17); the
period selector and drill-down arrive next. No deployment or push. Record red/green commands, behavioral demo, review findings/fixes,
local versus actual-host results, unresolved limits and commit reference when
available. Passing local tests alone cannot close a required real-host gate.
