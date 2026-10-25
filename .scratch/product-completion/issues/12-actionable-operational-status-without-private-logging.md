# 12: Actionable operational status without private logging

Status: ready-for-agent
Approval: task division approved by Sourav; planning/publication only.
Execution authorization: PAUSED — requires Sourav's explicit implementation instruction.
Blocked by: [04](./04-understand-and-recover-an-upload-s-processing-state.md), [07](./07-advisory-failure-and-separate-bounded-recovery.md), [09](./09-preserve-financial-results-and-corrections-across-interruptions.md), [10](./10-consistent-scheduled-backup-with-safe-retention.md)
Draft reference: T11
Parent: [Authoritative completion specification](../spec.md)
Historical evidence: [22](../../initial-release/issues/22-expose-operational-failures-without-logging-private-contents.md)

## What to deliver

Actionable operational status without private logging. Complete the end-to-end behavior below, reusing verified existing work rather than rebuilding it.

## Acceptance criteria

- [ ] Surface processing/advice/backup last success and unresolved failure with next
  action, distinguishing running services from functional readiness.
- [ ] Normal use remains independent of laptop/NAS availability; diagnostics contain
  neither original financial contents nor credentials.
- [ ] Each producer task exposes its own honest status; this task integrates those
  statuses, not a generic telemetry platform.

## Decision and external gates

No additional design gate identified. Shared authorization and safety gates still apply.
Read the [decision register](../spec.md#decision-register). A resolved decision does not authorize coding or live changes.

## Verification

Browser status/failure journeys with producer data and privacy inspection of sanitized operational diagnostics.

Follow [common completion rules](../spec.md#completion-rules): TDD for changed public behavior, runtime/browser proof, standards and spec review, and separate local/host evidence.

## Current evidence and completion

Not accepted as complete. Historical references are evidence inputs, not closure of this task. No new implementation is authorized by publication.
Record exercised commands/scenarios, results, review findings, remaining gates and explicit commit references before closure.
