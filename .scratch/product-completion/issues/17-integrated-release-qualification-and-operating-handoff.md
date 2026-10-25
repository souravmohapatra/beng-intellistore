# 17: Integrated release qualification and operating handoff

Status: needs-info
Approval: task division approved by Sourav; planning/publication only.
Execution authorization: PAUSED — requires Sourav's explicit implementation instruction.
Blocked by: [11](./11-qualify-real-host-scheduling-wake-and-keep-awake-lifecycle.md), [13](./13-restore-and-verify-a-recovery-generation-in-isolation.md), [14](./14-verify-actual-supplied-statement-families-end-to-end.md), [15](./15-measure-and-meet-real-host-dashboard-search-latency.md), [16](./16-accept-complete-desktop-keyboard-and-actual-phone-journeys.md)
Draft reference: T17
Parent: [Authoritative completion specification](../spec.md)
Historical evidence: [29](../../initial-release/issues/29-qualify-the-complete-deterministic-release-on-real-hosts.md), [30](../../initial-release/issues/30-record-release-evidence-and-a-reviewable-milestone-handoff.md)

## What to deliver

Integrated release qualification and operating handoff. Complete the end-to-end behavior below, reusing verified existing work rather than rebuilding it.

## Acceptance criteria

- [ ] Map every applicable AC-01–27 to observed local and real-host evidence;
  no unrun/failed criterion silently disappears.
- [ ] Verify ordinary use without laptop/NAS, approved update/restart/rollback,
  runtime configuration, privacy and recovery procedure.
- [ ] Deliver reviewable release evidence and operating instructions for Sourav's
  acceptance. Final release/deployment and push still require explicit approval.

## Decision and external gates

D4: final release/deployment acceptance; push is separately authorized.
Read the [decision register](../spec.md#decision-register). A resolved decision does not authorize coding or live changes.

## Verification

AC-01–27 evidence ledger, integrated real-host checks and reviewed operating/recovery handoff.

Follow [common completion rules](../spec.md#completion-rules): TDD for changed public behavior, runtime/browser proof, standards and spec review, and separate local/host evidence.

## Current evidence and completion

Not accepted as complete. Historical references are evidence inputs, not closure of this task. No new implementation is authorized by publication.
Record exercised commands/scenarios, results, review findings, remaining gates and explicit commit references before closure.
