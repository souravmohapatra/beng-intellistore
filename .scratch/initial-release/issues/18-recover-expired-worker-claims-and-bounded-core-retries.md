# 18: Recover expired worker claims and bounded core retries

Status: ready-for-agent
Claimed by: Codex
Approval: ticket breakdown approved by Sourav
Blocked by: 04
Parent: [First-release specification](../spec.md)
Acceptance trace: AC-15, AC-16, AC-20
Worker routing: Stronger implementation/design oversight and independent review recommended.

## What to build

Interrupted processing becomes retryable without stale ownership or an endless retry loop, with visible recovery status.

## Acceptance criteria

- [ ] Renew claims via worker progress; expiry allows retry and the worker stops when lost ownership is detected.
- [ ] Transient core failures get at most three total attempts with increasing delays, then visible failure/manual retry; deterministic validation failures go to review.
- [ ] Wake/readiness checks do not consume processing attempts; one failed upload does not block other eligible uploads.
- [ ] Restart cleans orphaned temporary worker files and recovers job state without losing accepted originals or committed data; record measured timing choices.

## Test interface and verification

Application job/result interfaces with real PostgreSQL and controllable clock/failures. Use independently reviewed expected values and the approved
interfaces. For new behavioral code, observe a failing test and implement the minimum slice,
then repeat. Evaluation/evidence work runs the relevant existing checks; do not
create contrived tests of documentation. Include usable integration and meaningful
tests with the behavior rather than leaving a parser or UI stub. Follow [shared execution rules](../ticket-plan.md#execution-proposal)
for review, host evidence and permission limits.

## Prerequisites and scope limit

P-06 claim/heartbeat/retry/execution timing calibration.

Optional advice failure does not use core import retry policy; this slice must not require a model.

## Completion evidence

Not started. Record red/green commands, behavioral demo, review findings/fixes,
local versus actual-host results, unresolved limits and commit reference when
available. Passing local tests alone cannot close a required real-host gate.

## Comments

### 2026-10-22 — Codex: local recovery verification

- The recorded red run had 212 tests with only `test_claim_sets_a_lease_and_progress_renews_it` failing: its progress request omitted the required `stage`, so the API correctly returned 400. The test now sends a valid progress event; no API behavior was changed for that failure.
- `./scripts/smoke.sh` passes: system check, migration drift check, 212 tests, and the two-process restart check (`restart check ok`).
- Local tests cover lease renewal/expiry, retry/backoff, the three-attempt cap, manual retry, failed-job isolation, and stale temporary-file cleanup. Current settings default to a 120-second lease and 30/120-second retry delays.
- Those timings are not measured on the target laptop/network. P-06 actual-host calibration remains open; do not close this ticket or claim target timing acceptance until measured there.
- No deployment or host contact performed; no commit yet.
