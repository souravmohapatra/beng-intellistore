# 06: One validated suggestion through explicit user confirmation

Status: done locally
Claimed by: —
Approval: task division approved by Sourav; planning/publication only.
Execution authorization: authorized by Sourav's instruction to implement the active backlog.
Blocked by: [05](./05-isolated-laptop-inference-runtime-and-worker-connectivity.md) — local contract delivered; real runtime demonstration remains open in05.
Draft reference: T06
Parent: [Authoritative completion specification](../spec.md)
Historical evidence: [27](../../initial-release/issues/27-show-validated-optional-advice-without-risking-financial-imports.md)

## What to deliver

One validated suggestion through explicit user confirmation. Complete the end-to-end behavior below, reusing verified existing work rather than rebuilding it.

## Acceptance criteria

- [x] Unresolved transaction → bounded local inference → validated source-linked
  classification or abstention → review → explicit confirmation or dismissal.
- [x] Preserve model/prompt version and provenance; suggestions cannot rewrite
  amounts, dates, balances or override confirmed corrections.
- [x] Demonstrate the whole path in isolation. task 08 gates normal-use enablement,
  not controlled evaluation; this avoids a qualification/implementation cycle.
- [x] Integrate with task 03 through the existing review interface; shared ownership
  must be coordinated, but visual polish is not a technical blocker.

## Decision and external gates

D2: advisory contract, persistence and confirmation semantics.
Read the [decision register](../spec.md#decision-register). A resolved decision does not authorize coding or live changes.

## Verification

Public advisory/review/report tests and an isolated real-runtime suggestion→confirmation demonstration; verify source facts and existing corrections unchanged.

Follow [common completion rules](../spec.md#completion-rules): TDD for changed public behavior, runtime/browser proof, standards and spec review, and separate local/host evidence.

## Current evidence and completion

Completed locally with controlled advisory responses; real-runtime inference and
the qualification gate remain tasks05/08.

Implementation:
- `ClassificationSuggestion` stores version, allowed classification, confidence,
  explanation, model and prompt version against one transaction. Results carry
  suggestions per source section; the application stores advice only for rows the
  deterministic rules leave unresolved and drops malformed, out-of-range or
  unknown-classification entries without failing the import.
- Review shows the open suggestion beside source evidence with explicit
  "Confirm suggested classification" (creates a normal Correction with provenance
  in its note) and "Dismiss suggestion" (no financial effect). Abstentions are not
  offered for confirmation.
- Worker requests advice only for rows whose source type looks unresolved, with
  bounded attempts; advice failure never fails the import.

Verification:
- `env POSTGRES_PORT=55487 .venv/bin/python manage.py test ledger.tests.test_advice worker.tests.test_advisory`:16 passed.
- Full suite:264 passed (one pre-existing intermittent LiveServer/flush race observed; rerun green).
- Browser against isolated PostgreSQL: seeded open suggestion rendered with model,
  prompt version, confidence, explanation and effect wording; confirming created
  the correction, closed the suggestion and showed it in history;390px no overflow.
- Malformed advice, unknown classification, out-of-range confidence and unknown
  source rows produced no suggestion while the import still succeeded.
- Actual model quality/fit is not claimed; enablement stays gated by task08.

Implementation commits: `0a8b173` (application integration), `17cf8da` (evaluation harness/runbook). No deployment or push.
