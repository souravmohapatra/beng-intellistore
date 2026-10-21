# 17: Apply cash refunds fee waivers and conversion returns

Status: done
Approval: ticket breakdown approved by Sourav
Blocked by: 14
Parent: [First-release specification](../spec.md)
Acceptance trace: AC-09, AC-10
Worker routing: Budget worker candidate; stronger review required before completion.

## What to build

The reporting/review flow handles agreed cash and reversal cases, including Revolut FX spending at the GBP boundary.

## Acceptance criteria

- [x] Cash withdrawal counts as spending and outgoing at posting without a cash ledger.
- [x] Refund/fee waiver/evidenced returned payment reverses its original classification; uncertain returns require review and are not automatic income.
- [x] GBP converted out counts as spending/outgoing; conversion back reduces spending in its posting period and records incoming GBP, not income.
- [x] Use independently calculated cross-period examples and ensure incoming reversals do not net down gross outgoing.

## Test interface and verification

Reporting/application review interfaces and visible transaction effects. Use independently reviewed expected values and the approved
interfaces. For new behavioral code, observe a failing test and implement the minimum slice,
then repeat. Evaluation/evidence work runs the relevant existing checks; do not
create contrived tests of documentation. Include usable integration and meaningful
tests with the behavior rather than leaving a parser or UI stub. Follow [shared execution rules](../ticket-plan.md#execution-proposal)
for review, host evidence and permission limits.

## Prerequisites and scope limit

Independent literal event examples, including unmatched returned payments.

No additional investment/crypto classification policy beyond confirmed review rules.

## Completion evidence

Machine rules: cash withdrawals remain spending and cash outgoing with no cash
ledger; negative fee charges (type or description containing FEE) are spending
and outgoing; refunds continue to reduce spending without becoming income;
GBP conversions count only with `Exchanged to` evidence — out is spending and
outgoing, back to GBP reduces spending in its own period and records incoming
cash without income.

Reversals: `ReversalLink` records a confirmed reversal of an evidenced original.
Candidates require the same account, an equal opposite amount, reversal wording
(REFUND/REVERSAL/RETURN/WAIVER/CHARGEBACK/REVERSED) on either row, and a
45-day display window — the window only decides what is offered, never that a
reversal happened. Direction is canonical (the hinted row, else the later row);
ambiguous directions and rows already reversed are rejected. Confirmation locks
both rows and saves only through the review UI.

Semantics: a confirmed reversal applies the inverse of the original's
spending/income in the reversal's posting period and leaves cash outgoing
unchanged, so incoming reversals never net down gross outgoing. Both source rows
and their locators remain.

Literal cross-period examples: £5 account fee in July (−500) and a confirmed
waiver in August → July spending/outgoing 500, August spending −500, income 0,
August outgoing 0. A returned £20 card payment → July spending/outgoing 2000,
August spending −2000, income 0, outgoing 0. An unmatched returned payment stays
unclassified and provisional with no income. £25 converted out in July and £10
back in August → July spending/outgoing 2500, August spending −1000, income 0.

Green: `.venv/bin/python manage.py test --noinput` → 201 tests OK;
`./scripts/smoke.sh` → exit 0, 201 tests, `restart check ok`.

Limits: candidates depend on reversal wording; unmatched or ambiguous returns
stay in review rather than becoming income; no cash-wallet ledger or
investment/crypto classification. No deployment or push. Record red/green commands, behavioral demo, review findings/fixes,
local versus actual-host results, unresolved limits and commit reference when
available. Passing local tests alone cannot close a required real-host gate.
