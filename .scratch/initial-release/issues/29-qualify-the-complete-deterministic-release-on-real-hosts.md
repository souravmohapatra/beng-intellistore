# 29: Qualify the complete release on real hosts

Status: ready-for-agent
Approval: ticket breakdown approved by Sourav
Blocked by: 10, 15, 16, 17, 19, 21, 22, 23, 25, 26, 27, 28
Parent: [First-release specification](../spec.md)
Acceptance trace: AC-01 through AC-27
Worker routing: Stronger implementation/design oversight and independent review recommended.

## What to build

The integrated application passes source accuracy, usable UI, qualified local advisory inference, private access, phone, failure and recovery gates on deployment hosts.

## Acceptance criteria

- [ ] Verify all four actual source families against private independent oracles outside Git; preserve known date-range and savings coverage gaps.
- [ ] Exercise the approved LAN-only login/authorization, real phone/desktop upload/search/review, concurrent correction/stale-result/retry recovery and source accessibility. VPN/TLS is deferred, not claimed verified.
- [ ] Verify laptop/NAS outage independence, wake/readiness/lease lifecycle, restart/schedule catch-up, backup during processing and isolated restore together.
- [ ] Demonstrate actual qualified laptop inference through suggestion review and explicit confirmation; model failure leaves import/manual review usable. A failed candidate evaluation requires Sourav's explicit release-scope decision.
- [ ] Run appropriate integrated regressions and privacy checks; record failures/untested items and fix via bounded follow-up work rather than silently waiving release criteria.
- [ ] Use fault simulation without deliberate power cuts; do not claim mini-PC or NAS physical power-loss protection.

## Test interface and verification

Actual-host application/browser/infrastructure interfaces. Use independently reviewed expected values and the approved
interfaces. For new behavioral code, observe a failing test and implement the minimum slice,
then repeat. Evaluation/evidence work runs the relevant existing checks; do not
create contrived tests of documentation. Include usable integration and meaningful
tests with the behavior rather than leaving a parser or UI stub. Follow [shared execution rules](../ticket-plan.md#execution-proposal)
for review, host evidence and permission limits.

## Prerequisites and scope limit

Approved deployment/fault scenarios, private source oracles and actual device/host availability.

This is an integration acceptance ticket, not permission for another broad rewrite. Both advice tickets and actual inference integration are required under the approved completion plan unless Sourav explicitly revises that boundary.

## Completion evidence

Not started. Record red/green commands, behavioral demo, review findings/fixes,
local versus actual-host results, unresolved limits and commit reference when
available. Passing local tests alone cannot close a required real-host gate.
