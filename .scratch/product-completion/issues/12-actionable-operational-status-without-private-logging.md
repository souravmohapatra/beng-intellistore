# 12: Actionable operational status without private logging

Status: done locally
Approval: task division approved by Sourav; planning/publication only.
Execution authorization: authorized by Sourav's instruction to implement the active backlog.
Blocked by: [04](./04-understand-and-recover-an-upload-s-processing-state.md), [07](./07-advisory-failure-and-separate-bounded-recovery.md), [09](./09-preserve-financial-results-and-corrections-across-interruptions.md), [10](./10-consistent-scheduled-backup-with-safe-retention.md) — producers now expose data; real NAS status appears when task10 runs.
Draft reference: T11
Parent: [Authoritative completion specification](../spec.md)
Historical evidence: [22](../../initial-release/issues/22-expose-operational-failures-without-logging-private-contents.md)

## What to deliver

Actionable operational status without private logging. Complete the end-to-end behavior below, reusing verified existing work rather than rebuilding it.

## Acceptance criteria

- [x] Surface processing/advice/backup last success and unresolved failure with next
  action, distinguishing running services from functional readiness.
- [x] Normal use remains independent of laptop/NAS availability; diagnostics contain
  neither original financial contents nor credentials.
- [x] Each producer task exposes its own honest status; this task integrates those
  statuses, not a generic telemetry platform.

## Decision and external gates

No additional design gate identified. Shared authorization and safety gates still apply.
Read the [decision register](../spec.md#decision-register). A resolved decision does not authorize coding or live changes.

## Verification

Browser status/failure journeys with producer data and privacy inspection of sanitized operational diagnostics.

Follow [common completion rules](../spec.md#completion-rules): TDD for changed public behavior, runtime/browser proof, standards and spec review, and separate local/host evidence.

## Current evidence and completion

Completed locally.

Implementation:
- Authenticated `/status/` surfaces processing counts and last completed upload,
  advice pending/processing/failed counts and last suggestion, and the last backup
  outcome (success/failed, generation, timestamp) read from a status file written
  by the backup container. Missing or corrupt status is stated honestly.
- Failure notices give the next action (open the upload receipt, retry advice,
  fix the destination and rerun). No financial contents, originals, credentials or
  model prompts are rendered or logged.
- Ordinary browsing never calls the laptop or NAS; the page reflects stored state.

Verification:
- `ledger.tests.test_status`:8tests covering login, absent/corrupt files,
  failed-attempt/last-success separation, recovery-window warnings, and actual
  result-completion ordering (not upload ID order).
- Real browser: status page showed current counts, last imported upload, last
  suggestion provenance and an honest "No backup outcome recorded";390px no overflow.
- The backup status writer is exercised by the real container proof in task10.
- Browser verified disabled-advice notice, no misleading request controls, and
  last-processing timestamp. Backup attempt and last successful generation remain
  separate after a real read-only-destination failure.

No deployment or push. Real NAS success/failure appears once the user runs task10.
