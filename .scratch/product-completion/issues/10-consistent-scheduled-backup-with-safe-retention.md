# 10: Consistent scheduled backup with safe retention

Status: needs-info
Approval: task division approved by Sourav; planning/publication only.
Execution authorization: PAUSED — requires Sourav's explicit implementation instruction.
Blocked by: None (technical dependencies only; authorization still required)
Draft reference: T12
Parent: [Authoritative completion specification](../spec.md)
Historical evidence: [24](../../initial-release/issues/24-create-consistent-backup-generations-with-visible-failure.md)

## What to deliver

Consistent scheduled backup with safe retention. Complete the end-to-end behavior below, reusing verified existing work rather than rebuilding it.

## Acceptance criteria

- [ ] Consistent database + originals + corrections recovery generation while
  imports/edits continue; define the committed-state boundary before coding.
- [ ] Run at 03:00 Europe/London; keep seven successful generations; retire an old
  generation only after a new complete success.
- [ ] Interrupted/full/unavailable NAS and schedule/DST/catch-up failures are visible;
  no local deletion and no disruption of normal application use.
- [ ] Prove locally, then on approved NAS destination. Resolve path/headroom,
  consistency protocol and target permissions before the relevant implementation.

## Decision and external gates

D3: backup consistency method, verified NAS destination/capacity and target approval.
Read the [decision register](../spec.md#decision-register). A resolved decision does not authorize coding or live changes.

## Verification

Concurrent import/correction during backup, retention/interruption/storage-failure tests locally; then approved real NAS generation.

Follow [common completion rules](../spec.md#completion-rules): TDD for changed public behavior, runtime/browser proof, standards and spec review, and separate local/host evidence.

## Current evidence and completion

Not accepted as complete. Historical references are evidence inputs, not closure of this task. No new implementation is authorized by publication.
Record exercised commands/scenarios, results, review findings, remaining gates and explicit commit references before closure.
