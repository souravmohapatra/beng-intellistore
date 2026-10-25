# 02: Evidence-first dashboard and transaction navigation

Status: done
Claimed by: —
Approval: task division approved by Sourav; planning/publication only.
Execution authorization: authorized by Sourav's instruction to implement the active backlog; no unresolved design gate.
Blocked by: None (technical dependencies only; authorization still required)
Draft reference: T02
Parent: [Authoritative completion specification](../spec.md)
Historical evidence: [12](../../initial-release/issues/12-show-dated-balances-and-gap-aware-period-history.md), [13](../../initial-release/issues/13-search-descriptions-and-drill-into-metric-evidence.md), [23](../../initial-release/issues/23-complete-phone-and-accessible-browser-journeys.md)

## What to deliver

Evidence-first dashboard and transaction navigation. Complete the end-to-end behavior below, reusing verified existing work rather than rebuilding it.

## Acceptance criteria

- [x] Approved A layout, real period-selected metrics, dated balances/history,
  provisional/disputed/unknown states and honest coverage gaps.
- [x] Metric and original-description search lead to supporting transactions and
  originals; period context and pagination survive navigation.
- [x] Demonstrate populated and empty states on desktop and narrow viewports.
  Reuse existing financial semantics and SVG evidence chart; no chart-library
  migration unless a concrete requirement justifies it.

## Decision and external gates

No additional design gate identified. Shared authorization and safety gates still apply.
Read the [decision register](../spec.md#decision-register). A resolved decision does not authorize coding or live changes.

## Verification

Independent expected financial totals; browser period/search/drilldown navigation, uncertainty and responsive rendering.

Follow [common completion rules](../spec.md#completion-rules): TDD for changed public behavior, runtime/browser proof, standards and spec review, and separate local/host evidence.

## Current evidence and completion

Completed locally by auditing preserved templates/context and exercising the
real production-mode application against isolated synthetic PostgreSQL/files.
Full257-test suite passed after presentation refinements, including independent
totals, missing/disputed evidence, periods, search and pagination.

Browser: August2026 retained; spending£1,053.20/income£2,500.00/outgoing£1,065.64/
net-cash£2,646.80 from imported fixture; second account explicitly unknown with
incomplete-net-cash warning. Spending drilldown retained dates and five
source-linked contributors. Date-filtered COFFEE search returned its source and
review links; unmatched query showed empty results. Invalid reversed period
showed fallback warning and retained input. Desktop and390px dashboard/metric/
search inspected without document overflow. Empty account/no-evidence states
covered by full suite and earlier browser evidence.

Review: financial semantics and SVG dated-point chart preserved; no fabricated
continuity, zero balances, model status or external assets. Actual-phone and
mini-PC performance remain tasks15/16. No new commit/deployment/push.

Implementation commit: `666045a` — responsive dashboard, navigation shell and search drilldown.
