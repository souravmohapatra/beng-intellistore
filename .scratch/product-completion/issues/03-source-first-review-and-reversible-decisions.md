# 03: Source-first review and reversible decisions

Status: done
Claimed by: —
Approval: task division approved by Sourav; planning/publication only.
Execution authorization: authorized by Sourav's instruction to implement the active backlog; no unresolved design gate.
Blocked by: None (technical dependencies only; authorization still required)
Draft reference: T03
Parent: [Authoritative completion specification](../spec.md)
Historical evidence: [14](../../initial-release/issues/14-review-and-reverse-a-correction-without-losing-history.md), [15](../../initial-release/issues/15-resolve-overlapping-imports-conservatively.md), [16](../../initial-release/issues/16-confirm-repayments-and-own-account-transfer-links.md), [17](../../initial-release/issues/17-apply-cash-refunds-fee-waivers-and-conversion-returns.md), [23](../../initial-release/issues/23-complete-phone-and-accessible-browser-journeys.md)

## What to deliver

Source-first review and reversible decisions. Complete the end-to-end behavior below, reusing verified existing work rather than rebuilding it.

## Acceptance criteria

- [x] Side-by-side source and decision on desktop; source accessible before actions
  on narrow screens. Reach review from transaction/search/metric journeys.
- [x] Confirm/revert classification, inspect history, resolve duplicate/transfer/
  repayment/reversal candidates without rewriting source facts.
- [x] Demonstrate changed reporting effect and restored effect after revert, plus
  rejected invalid decisions and preserved history.

## Decision and external gates

No additional design gate identified. Shared authorization and safety gates still apply.
Read the [decision register](../spec.md#decision-register). A resolved decision does not authorize coding or live changes.

## Verification

Public review/report behavioral tests and browser confirm → reporting change → revert → restored effect; candidate decisions and invalid requests.

Follow [common completion rules](../spec.md#completion-rules): TDD for changed public behavior, runtime/browser proof, standards and spec review, and separate local/host evidence.

## Current evidence and completion

Completed locally. Review list and side-by-side review detail surfaces implemented and verified.
Tested:
- Full review suite (review, overlap, reversals, transfers): 47 tests passed.
- Real browser: unknown correction moved spending £1,053.20 -> £1,050.00 with provisional warning; revert restored £1,053.20 and marked history entry as reverted; invalid classification on debit was rejected with 400.

Implementation commit: `74541ea` — source-first review and reversible decision presentation.
