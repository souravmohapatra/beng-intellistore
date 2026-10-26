# 14: Verify actual supplied statement families end to end

Status: needs-info
Approval: task division approved by Sourav; planning/publication only.
Execution authorization: authorized; supplied originals exercised locally.
Blocked by: D4 independent full-field oracle and additional actual edge-case evidence;09 is done.
Draft reference: T14
Parent: [Authoritative completion specification](../spec.md)
Historical evidence: [06](../../initial-release/issues/06-verify-the-first-private-deployment-milestone.md), [07](../../initial-release/issues/07-import-lloyds-credit-with-posting-dates-and-separate-fees.md), [08](../../initial-release/issues/08-import-amex-without-duplicating-annual-or-fx-totals.md), [09](../../initial-release/issues/09-import-revolut-personal-gbp-while-ignoring-excluded-sections.md), [10](../../initial-release/issues/10-add-savings-mapping-and-independent-account-section-outcomes.md), [15](../../initial-release/issues/15-resolve-overlapping-imports-conservatively.md), [16](../../initial-release/issues/16-confirm-repayments-and-own-account-transfer-links.md), [17](../../initial-release/issues/17-apply-cash-refunds-fee-waivers-and-conversion-returns.md), [29](../../initial-release/issues/29-qualify-the-complete-deterministic-release-on-real-hosts.md)

## What to deliver

Verify actual supplied statement families end to end. Complete the end-to-end behavior below, reusing verified existing work rather than rebuilding it.

## Acceptance criteria

- [ ] Compare Lloyds Current/Credit, Amex and included Revolut GBP/savings against
  independently established expected results, using private files outside Git.
- [ ] Include overlap, repayments, transfers, cash/refunds, excluded sections,
  missing savings coverage, mismatch and partial-section outcomes.
- [x] Existing parsers are not rebuilt. Record exact supported-format limits and
  fix proven discrepancies only within approved implementation scope.

## Decision and external gates

D4: private source fixtures and independent expected results available outside Git.
Read the [decision register](../spec.md#decision-register). A resolved decision does not authorize coding or live changes.

## Verification

Actual private originals with independent expected values across all supported families; retain sanitized outcome evidence only.

Follow [common completion rules](../spec.md#completion-rules): TDD for changed public behavior, runtime/browser proof, standards and spec review, and separate local/host evidence.

## Current evidence and completion

The four supplied originals are already available outside Git and have now been
exercised locally through the real UI and worker API. Full source-oracle and
edge-case acceptance remains open; do not ask for the same originals again.

Local evidence (synthetic fixtures with independently established expectations):
- `test_lloyds_current*`, `test_lloyds_credit`, `test_amex`, `test_revolut`
  cover exact amounts/dates/balances and supported-format limits.
- `test_overlap`, `test_reversals`, `test_transfers`, `test_review` cover
  duplicate/overlap decisions, repayments, transfers, cash withdrawals and refunds.
- Revolut tests cover personal GBP only, excluded joint/non-GBP/crypto sections,
  savings mapping, missing savings coverage and partial-section publication.
- Latest clean `./scripts/smoke.sh`:377 tests, migration drift check and restart
  proof pass. Two actual-format mismatches were fixed with sanitized regressions:
  Amex arithmetic summary-box balances/credits/debits, and Lloyds Credit
  four-digit card columns, pound-prefixed totals and spaced credit markers.
- Actual supplied PDFs: browser created/selects accounts, uploaded each source,
  Process now released four jobs, and the worker returned four imported outcomes.
  Counts match prior independent inventory: Current17, Lloyds Credit78, Amex13,
  Revolut personal GBP10. All source reconciliation gates pass.
- Original downloads match all four inputs byte-for-byte. Publication retained
  parsed dates, amounts, descriptions and source locations. Browser dashboard
  cards, spending drilldown, description search and source review were exercised.
  Private original contents and monetary values remain outside Git.
- Independent reviewers checked parser validation and reporting changes. Amex's
  source-stated debit total is checked separately, not inferred from parsed rows.

Remaining acceptance inputs: a privately established per-row expected-results
oracle and actual examples covering overlap, repayment/transfer confirmation,
refunds and savings/partial-section edges not established by these four samples.
Synthetic regressions cover those behaviors but do not substitute for the
required private-source acceptance.
Private files and expected values must not enter the repository.
