# 13: Restore and verify a recovery generation in isolation

Status: needs-info
Approval: task division approved by Sourav; planning/publication only.
Execution authorization: PAUSED — requires Sourav's explicit implementation instruction.
Blocked by: [10](./10-consistent-scheduled-backup-with-safe-retention.md)
Draft reference: T13
Parent: [Authoritative completion specification](../spec.md)
Historical evidence: [25](../../initial-release/issues/25-restore-originals-records-and-corrections-into-isolation.md)

## What to deliver

Restore and verify a recovery generation in isolation. Complete the end-to-end behavior below, reusing verified existing work rather than rebuilding it.

## Acceptance criteria

- [ ] Restore into a separate database/storage target; verify original bytes,
  evidence navigation, reports, mappings and confirmed corrections.
- [ ] Reject incomplete/unusable generations and report measured recovery steps
  and recovery-window limits; never overwrite the live database for a test.
- [ ] Requires approval for actual NAS/host restore exercise and isolated capacity.

## Decision and external gates

D3/D4: isolated restore capacity and approved NAS/host exercise.
Read the [decision register](../spec.md#decision-register). A resolved decision does not authorize coding or live changes.

## Verification

Isolated restore from successful generation, byte comparisons and public evidence/report/correction checks; incomplete-generation rejection.

Follow [common completion rules](../spec.md#completion-rules): TDD for changed public behavior, runtime/browser proof, standards and spec review, and separate local/host evidence.

## Current evidence and completion

Not accepted as complete. Historical references are evidence inputs, not closure of this task. No new implementation is authorized by publication.
Record exercised commands/scenarios, results, review findings, remaining gates and explicit commit references before closure.
