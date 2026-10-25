# 14: Verify actual supplied statement families end to end

Status: needs-info
Approval: task division approved by Sourav; planning/publication only.
Execution authorization: PAUSED — requires Sourav's explicit implementation instruction.
Blocked by: [09](./09-preserve-financial-results-and-corrections-across-interruptions.md)
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
- [ ] Existing parsers are not rebuilt. Record exact supported-format limits and
  fix proven discrepancies only within approved implementation scope.

## Decision and external gates

D4: private source fixtures and independent expected results available outside Git.
Read the [decision register](../spec.md#decision-register). A resolved decision does not authorize coding or live changes.

## Verification

Actual private originals with independent expected values across all supported families; retain sanitized outcome evidence only.

Follow [common completion rules](../spec.md#completion-rules): TDD for changed public behavior, runtime/browser proof, standards and spec review, and separate local/host evidence.

## Current evidence and completion

Not accepted as complete. Historical references are evidence inputs, not closure of this task. No new implementation is authorized by publication.
Record exercised commands/scenarios, results, review findings, remaining gates and explicit commit references before closure.
