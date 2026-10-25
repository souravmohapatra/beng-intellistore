# 09: Preserve financial results and corrections across interruptions

Status: done locally
Claimed by: —
Approval: task division approved by Sourav; planning/publication only.
Execution authorization: authorized by Sourav's instruction to implement the active backlog.
Blocked by: None (technical dependencies only; authorization still required)
Draft reference: T09
Parent: [Authoritative completion specification](../spec.md)
Historical evidence: [18](../../initial-release/issues/18-recover-expired-worker-claims-and-bounded-core-retries.md), [19](../../initial-release/issues/19-fence-stale-results-and-preserve-corrections-across-lost-acknowledgements.md)

## What to deliver

Preserve financial results and corrections across interruptions. Complete the end-to-end behavior below, reusing verified existing work rather than rebuilding it.

## Acceptance criteria

- [x] Verify/fill gaps in bounded lease recovery, lost-ack replay, conflicting
  payloads, stale attempts, concurrent corrections and changed-identity reprocessing.
- [x] Interrupted or repeated work cannot duplicate financial effects or replace
  newer results/user corrections; source/history remains available.
- [x] Use real PostgreSQL/files and approved controlled interfaces. Host calibration no longer blocks local historical-ticket19 work; task11
  retains mandatory real-host acceptance under the approved division.

## Decision and external gates

No additional design gate identified. Shared authorization and safety gates still apply.
Read the [decision register](../spec.md#decision-register). A resolved decision does not authorize coding or live changes.

## Verification

Public application/worker interfaces with PostgreSQL/files; lost acknowledgements, stale jobs, concurrent correction, and replay consistency scenarios.

Follow [common completion rules](../spec.md#completion-rules): TDD for changed public behavior, runtime/browser proof, standards and spec review, and separate local/host evidence.

## Current evidence and completion

Completed locally. No new production code was needed for job-result integrity; gaps
were closed with behavioral coverage plus one new durable-correction scenario.

Verified behavior:
- Expired attempt → retried and counted; backoff respected; third failure fails
  visibly with manual retry; failed upload does not block others.
- Heartbeat/progress renew the lease; a lost lease returns409; a stale worker's
  result cannot attach to a newer attempt.
- Identical result resubmission returns the recorded outcome (`already_recorded`)
  without duplicate effects; a conflicting payload for the same attempt returns
  409 and keeps the first result.
- Confirmed duplicate/transfer/reversal decisions retain both source rows;
  reciprocal duplicates cannot erase all effects.
- New `ledger.tests.test_integrity`: a confirmed correction survives re-import of
  the same original (duplicate outcome, six transactions before/after, correction
  history intact and still active).
- Changed-identity/mapping mismatch is rejected for consolidated sources by the
  existing published-section/source-mapping checks.
- Advice claims are fenced by credential, token and lease so stale advice cannot
  complete a newer claim (see task07).

Verification:
- `env POSTGRES_PORT=55487 .venv/bin/python manage.py test -v 0`:278 tests passed.
- Real local PostgreSQL/files and worker/API round trips used throughout.
- Host power/timing calibration remains task11 as agreed.

No implementation commit beyond test coverage and the advice fence; existing
recovery code was retained. Local evidence only; no push.
