# 28: Evaluate up to two local advice candidates before enablement

Status: ready-for-agent
Approval: ticket breakdown approved by Sourav
Blocked by: 06, 27
Parent: [First-release specification](../spec.md)
Acceptance trace: AC-26
Worker routing: Stronger implementation/design oversight and independent review recommended.

## What to build

A documented actual-laptop evaluation either selects a passing local candidate or records that advice stays disabled.

## Acceptance criteria

- [ ] Check current primary runtime/model/license/compatibility documentation, pin at most two quantized candidates and prepare Docker GPU integration before authorized model workload.
- [ ] Independently label 50 held-out ambiguous/unresolved cases including legitimate unknowns; keep prompt-development cases separate.
- [ ] Require at least 90% correct non-abstained suggestions and 50% coverage; report counts, per-class failures and rules-only baseline without hold-out tuning.
- [ ] Measure separate warm 100-item workload within ten minutes, cold load and memory/OOM behavior on existing hardware.
- [ ] Record exact artifacts/runtime/settings and disposition; a failed benchmark can complete this evaluation task with advice disabled, but cannot pass AC-26 or block deterministic release.

## Test interface and verification

Actual model adapter and operational evaluation interface; independent held-out dataset. Use independently reviewed expected values and the approved
interfaces. For new behavioral code, observe a failing test and implement the minimum slice,
then repeat. Evaluation/evidence work runs the relevant existing checks; do not
create contrived tests of documentation. Include usable integration and meaningful
tests with the behavior rather than leaving a parser or UI stub. Follow [shared execution rules](../ticket-plan.md#execution-proposal)
for review, host evidence and permission limits.

## Prerequisites and scope limit

P-08 independent labels and authorized actual-laptop model/container work.

No arbitrary model choice, cloud fallback or repeated tuning against the held-out score.

## Completion evidence

Not started. Record red/green commands, behavioral demo, review findings/fixes,
local versus actual-host results, unresolved limits and commit reference when
available. Passing local tests alone cannot close a required real-host gate.
