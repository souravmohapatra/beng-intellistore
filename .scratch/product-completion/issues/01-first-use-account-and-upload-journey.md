# 01: First-use account and upload journey

Status: done
Claimed by: —
Approval: task division approved by Sourav; planning/publication only.
Execution authorization: Sourav explicitly instructed implementation from the authoritative backlog; task01 has no unresolved design gate.
Blocked by: None (technical dependencies only; authorization still required)
Draft reference: T01
Parent: [Authoritative completion specification](../spec.md)
Historical evidence: [01](../../initial-release/issues/01-open-a-private-local-account-overview.md), [02](../../initial-release/issues/02-preserve-an-upload-and-reopen-its-original.md), [03](../../initial-release/issues/03-explain-intake-rejection-and-account-mismatches.md), [23](../../initial-release/issues/23-complete-phone-and-accessible-browser-journeys.md)

## What to deliver

First-use account and upload journey. Complete the end-to-end behavior below, reusing verified existing work rather than rebuilding it.

## Acceptance criteria

- [x] Sign in, create a named account, upload its first supported statement and reopen
  the preserved original without Django admin; validation and rejection are clear.
- [x] Duplicate/invalid account submissions cannot corrupt existing accounts; last
  account selection and consolidated savings mapping remain usable.
- [x] Audit and finish the preserved onboarding/UI work; demonstrate empty and
  successful journeys against real local PostgreSQL and isolated files.
- [x] Excludes account deletion/type changes; any broader account-management need
  requires explicit scope agreement.

## Decision and external gates

No additional design gate identified. Shared authorization and safety gates still apply.
Read the [decision register](../spec.md#decision-register). A resolved decision does not authorize coding or live changes.

## Verification

Authenticated HTTP tests with real PostgreSQL/files; browser first-use, rejection and original-reopen journey.

Follow [common completion rules](../spec.md#completion-rules): TDD for changed public behavior, runtime/browser proof, standards and spec review, and separate local/host evidence.

## Current evidence and completion

Completed locally after explicit implementation authorization. Audited preserved
AccountForm/AccountListView, authenticated route and account/upload/original
screens. Reused existing behavior; account list rows now use shared account-card
styling. No account delete/type-edit controls added.

Verification:
- Targeted onboarding/preservation/intake tests:23 passed.
- `env POSTGRES_PORT=55487 .venv/bin/python manage.py test -v 1`:257 passed,
  including savings mapping recall and empty-state coverage.
- Production-mode local Gunicorn/WhiteNoise with isolated PostgreSQL/files:
  sign-in → create current account → selected upload account → upload supported
  synthetic PDF → reopen original (HTTP200, application/pdf,3073bytes, PDF signature).
  Existing-file/account warning remained visible; missing-file rejection left
  existing receipts accessible.
- Duplicate name with different kind: visible error and aria-invalid=true;
  existing account stayed Current account.
- Inspected390px receipt/validation without document overflow and1440px account
  screen; no browser errors. Not actual-phone evidence.

Standards/spec review: login/CSRF protection and account-kind validation retained;
source preservation and rejection behavior unchanged. No real-host deployment,
live migration or push. Local changes not committed yet. Actual-device
acceptance remains task16; later dashboard/review acceptance is not claimed.

Implementation commit: `fe55d81` — authenticated named-account onboarding
(form/view/route, account screen and boundary tests). Shared presentation and
planning changes remain separate working-tree changes; no push.
