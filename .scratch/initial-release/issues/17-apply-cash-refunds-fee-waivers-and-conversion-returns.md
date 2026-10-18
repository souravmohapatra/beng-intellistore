# 17: Apply cash refunds fee waivers and conversion returns

Status: ready-for-agent
Approval: ticket breakdown approved by Sourav
Blocked by: 14
Parent: [First-release specification](../spec.md)
Acceptance trace: AC-09, AC-10
Worker routing: Budget worker candidate; stronger review required before completion.

## What to build

The reporting/review flow handles agreed cash and reversal cases, including Revolut FX spending at the GBP boundary.

## Acceptance criteria

- [ ] Cash withdrawal counts as spending and outgoing at posting without a cash ledger.
- [ ] Refund/fee waiver/evidenced returned payment reverses its original classification; uncertain returns require review and are not automatic income.
- [ ] GBP converted out counts as spending/outgoing; conversion back reduces spending in its posting period and records incoming GBP, not income.
- [ ] Use independently calculated cross-period examples and ensure incoming reversals do not net down gross outgoing.

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

Not started. Record red/green commands, behavioral demo, review findings/fixes,
local versus actual-host results, unresolved limits and commit reference when
available. Passing local tests alone cannot close a required real-host gate.
