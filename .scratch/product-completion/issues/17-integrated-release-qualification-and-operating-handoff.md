# 17: Integrated release qualification and operating handoff

Status: needs-info
Approval: task division approved by Sourav; planning/publication only.
Execution authorization: authorized; ledger and handoff drafted.
Blocked by: host/user gates in tasks08,10,11,13–16.
Draft reference: T17
Parent: [Authoritative completion specification](../spec.md)
Historical evidence: [29](../../initial-release/issues/29-qualify-the-complete-deterministic-release-on-real-hosts.md), [30](../../initial-release/issues/30-record-release-evidence-and-a-reviewable-milestone-handoff.md)

## What to deliver

Integrated release qualification and operating handoff. Complete the end-to-end behavior below, reusing verified existing work rather than rebuilding it.

## Acceptance criteria

- [x] Map every applicable AC-01–27 to observed local and real-host evidence;
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

Drafted; host/user gates remain.

Deliverables:
- [Release evidence ledger](release-ledger.md) maps AC-01–27 to current local,
  host and user gates. Every row has a disposition; unrun host gates are explicit.
- Operating handoff links the inference, backup and restore runbooks plus the
  Compose/systemd configuration. No secrets or private data are included.
- Ordinary-use independence is built and locally tested; update/rollback and
  real-host verification still require the approved deployment.

Remaining user-run steps: complete tasks08,10,11,13–16 on the actual hosts and
device, update the ledger with commands/results/limits, then accept or reject the
release. Deployment and push remain separately authorized.
