# 15: Measure and meet real-host dashboard/search latency

Status: needs-info
Approval: task division approved by Sourav; planning/publication only.
Execution authorization: PAUSED — requires Sourav's explicit implementation instruction.
Blocked by: [02](./02-evidence-first-dashboard-and-transaction-navigation.md)
Draft reference: T15
Parent: [Authoritative completion specification](../spec.md)
Historical evidence: [26](../../initial-release/issues/26-measure-and-meet-dashboard-and-search-latency.md)

## What to deliver

Measure and meet real-host dashboard/search latency. Complete the end-to-end behavior below, reusing verified existing work rather than rebuilding it.

## Acceptance criteria

- [ ] On an approved isolated mini-PC deployment, use 100,000 synthetic transactions
  spanning up to ten years; at least 30 warm repetitions per representative
  dashboard/period/search journey, p95 at most two seconds.
- [ ] Report cold first load, dataset/query/browser/network/runtime conditions;
  optimize and repeat only where needed. Never seed benchmark data into live DB.
- [ ] Requires an actual-host deployment baseline and resource approval; does not
  wait for unrelated wake/backup work.

## Decision and external gates

D4: isolated mini-PC benchmark deployment and resource approval.
Read the [decision register](../spec.md#decision-register). A resolved decision does not authorize coding or live changes.

## Verification

Actual mini-PC browser end-to-end latency report: cold load plus at least30 warm repetitions per journey, p95 and conditions.

Follow [common completion rules](../spec.md#completion-rules): TDD for changed public behavior, runtime/browser proof, standards and spec review, and separate local/host evidence.

## Current evidence and completion

Not accepted as complete. Historical references are evidence inputs, not closure of this task. No new implementation is authorized by publication.
Record exercised commands/scenarios, results, review findings, remaining gates and explicit commit references before closure.
