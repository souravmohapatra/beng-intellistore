# 04: Understand and recover an upload's processing state

Status: done
Claimed by: —
Approval: task division approved by Sourav; planning/publication only.
Execution authorization: PAUSED — requires Sourav's explicit implementation instruction.
Blocked by: None (technical dependencies only; authorization still required)
Draft reference: T04
Parent: [Authoritative completion specification](../spec.md)
Historical evidence: [18](../../initial-release/issues/18-recover-expired-worker-claims-and-bounded-core-retries.md), [20](../../initial-release/issues/20-release-nightly-work-and-show-process-now-progress.md), [23](../../initial-release/issues/23-complete-phone-and-accessible-browser-journeys.md)

## What to deliver

Understand and recover an upload's processing state. Complete the end-to-end behavior below, reusing verified existing work rather than rebuilding it.

## Acceptance criteria

- [x] Receipt distinguishes preserved, queued, processing, imported, partial,
  unsupported and failed states; shows actionable next steps and original access.
- [x] Process now and bounded retry reach real worker outcomes; worker unavailable
  does not prevent ordinary browsing or accepted-original access.
- [x] Exercise real local worker/API round trips and failure states; actual wake and
  target timing qualification belong to task 11.

## Decision and external gates

No additional design gate identified. Shared authorization and safety gates still apply.
Read the [decision register](../spec.md#decision-register). A resolved decision does not authorize coding or live changes.

## Verification

Real local worker/API smoke, controlled worker failure/retry, and browser receipt/status transitions.

Follow [common completion rules](../spec.md#completion-rules): TDD for changed public behavior, runtime/browser proof, standards and spec review, and separate local/host evidence.

## Current evidence and completion

Completed locally. Upload listing, receipt details, processing queue controls and retry flow implemented and verified.
Tested:
- Jobs test suite: 65 tests passed (claims, heartbeats, progress, results, retries, worker roundtrips).
- Real local worker and API roundtrip verified: uploaded statement, released with Process Now, worker claimed and processed, receipt updated to completed with preserved original access.

Implementation commit: `8b71927` — responsive upload receipt and processing status presentation.
