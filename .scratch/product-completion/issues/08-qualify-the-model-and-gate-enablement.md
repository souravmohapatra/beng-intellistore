# 08: Qualify the model and gate enablement

Status: needs-info
Approval: task division approved by Sourav; planning/publication only.
Execution authorization: PAUSED — requires Sourav's explicit implementation instruction.
Blocked by: [05](./05-isolated-laptop-inference-runtime-and-worker-connectivity.md), [06](./06-one-validated-suggestion-through-explicit-user-confirmation.md), [07](./07-advisory-failure-and-separate-bounded-recovery.md)
Draft reference: T08
Parent: [Authoritative completion specification](../spec.md)
Historical evidence: [28](../../initial-release/issues/28-evaluate-up-to-two-local-advice-candidates-before-enablement.md)

## What to deliver

Qualify the model and gate enablement. Complete the end-to-end behavior below, reusing verified existing work rather than rebuilding it.

## Acceptance criteria

- [ ] Establish independent development/held-out labels before tuning; evaluate at
  most two candidates and compare with the rules-only baseline.
- [ ] At least 50 held-out cases; at least 90% correctness among non-abstained
  suggestions and at least 50% coverage; report per-class failures.
- [ ] Actual laptop: 100 warm unresolved items within 10 minutes, cold load
  separately, memory recorded and no OOM; enable only a pinned passing candidate.
- [ ] Both fail → keep advice disabled and return to Sourav for an explicit decision.
  This is not permission to declare deterministic-only completion.

## Decision and external gates

D1/D2: pinned candidates and independently approved evaluation labels; laptop benchmark approval.
Read the [decision register](../spec.md#decision-register). A resolved decision does not authorize coding or live changes.

## Verification

Held-out report with case counts, abstentions, per-class precision/coverage, rules baseline, timings and memory; label provenance kept private.

Follow [common completion rules](../spec.md#completion-rules): TDD for changed public behavior, runtime/browser proof, standards and spec review, and separate local/host evidence.

## Current evidence and completion

Not accepted as complete. Historical references are evidence inputs, not closure of this task. No new implementation is authorized by publication.
Record exercised commands/scenarios, results, review findings, remaining gates and explicit commit references before closure.
