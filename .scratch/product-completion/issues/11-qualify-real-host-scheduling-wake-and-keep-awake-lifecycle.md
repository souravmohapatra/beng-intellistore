# 11: Qualify real-host scheduling, wake and keep-awake lifecycle

Status: needs-info
Approval: task division approved by Sourav; planning/publication only.
Execution authorization: authorized; local scheduling/wake code retains tests.
Blocked by: [09](./09-preserve-financial-results-and-corrections-across-interruptions.md) (done), [08](./08-qualify-the-model-and-gate-enablement.md), and D4 host/power approval.
Draft reference: T10
Parent: [Authoritative completion specification](../spec.md)
Historical evidence: [06](../../initial-release/issues/06-verify-the-first-private-deployment-milestone.md), [18](../../initial-release/issues/18-recover-expired-worker-claims-and-bounded-core-retries.md), [20](../../initial-release/issues/20-release-nightly-work-and-show-process-now-progress.md), [21](../../initial-release/issues/21-integrate-bounded-laptop-wake-and-keep-awake-leases.md)

## What to deliver

Qualify real-host scheduling, wake and keep-awake lifecycle. Complete the end-to-end behavior below, reusing verified existing work rather than rebuilding it.

## Acceptance criteria

- [ ] Verify LAN deployment baseline, nightly scheduling/restart catch-up, Process
  now, no wake for empty work and real worker-readiness transitions.
- [ ] Demonstrate wake → claim → bounded owned lease → result → release, expiry,
  failures and suspend/resume without touching unrelated leases/services.
- [ ] Calibrate timings against qualified workloads. Parser/controller checks can
  start earlier; final combined acceptance waits for task 08.
- [ ] Requires approved host deployment, power/fault scenarios and safe timing window.

## Decision and external gates

D4: deployment inventory and approved power/fault window; task 08 gates final workload calibration.
Read the [decision register](../spec.md#decision-register). A resolved decision does not authorize coding or live changes.

Task09 blocks local integrity prerequisites. Task08 is a completion gate for final combined-workload timing; parser/controller inspection may proceed earlier only when separately authorized.

## Verification

Actual-host scheduling/controller/worker evidence, approved failure/expiry/suspend scenarios and measured combined-workload timings.

Follow [common completion rules](../spec.md#completion-rules): TDD for changed public behavior, runtime/browser proof, standards and spec review, and separate local/host evidence.

## Current evidence and completion

Local scheduling/readiness/lease behavior is covered; real-host qualification and
timing calibration remain.

Local evidence:
- `jobs.tests.test_scheduling`, `test_readiness`, `test_keep_awake`,
  `test_controller` cover nightly release/catch-up, Process now, readiness states,
  wake request boundaries, owned leases, expiry/renewal and failure handling.
- Expired attempt recovery and bounded retries are covered in `test_recovery`.
- Full suite:327 tests passing; no host was contacted for power/fault actions.

Remaining user-run steps (approved window): verify LAN deployment baseline and
real wake→ready→claim→result→release, deny/unavailable controller, expiry,
suspend/resume, and no wake for empty work. Record timings and confirm unrelated
leases/services are untouched. Final combined parser+advice timing awaits task08.
