# 03: Explain intake rejection and account mismatches

> Historical completed work; not an active task. Preserve evidence below. Use the [authoritative backlog](../../product-completion/ticket-plan.md).

Status: done
Claimed by: —
Approval: ticket breakdown approved by Sourav
Blocked by: 02
Parent: [First-release specification](../spec.md)
Acceptance trace: AC-02, AC-03
Worker routing: Budget worker candidate; stronger review required before completion.

## What to build

The upload flow explains rejected files, preserves readable unsupported layouts and flags source/account mismatches.

## Acceptance criteria

- [x] Reject corrupt, password-protected and image-only inputs with distinct usable messages; enforce 20 MiB and 100 PDF pages including boundary cases.
- [x] Check content rather than extension; readable unsupported formats remain preserved with explicit unsupported status and no financial-import success.
- [x] Remember the selected named account and make detectable account identity mismatches visible without silent reassignment.
- [x] Recognize only fixture-backed layouts; text/CSV acceptance does not imply arbitrary extraction support.

## Test interface and verification

Application intake interface and browser upload/status journey. Use independently reviewed expected values and the approved
interfaces. For new behavioral code, observe a failing test and implement the minimum slice,
then repeat. Evaluation/evidence work runs the relevant existing checks; do not
create contrived tests of documentation. Include usable integration and meaningful
tests with the behavior rather than leaving a parser or UI stub. Follow [shared execution rules](../ticket-plan.md#execution-proposal)
for review, host evidence and permission limits.

## Prerequisites and scope limit

P-03 safe rejection/identity fixtures.

No universal parser, password workflow or OCR.

## Completion evidence

Intake now decides from bytes: `intake/inspect.py` rejects >20 MiB (413), damaged
or unreadable PDFs, password-protected PDFs, image-only PDFs (no extractable
text) and non-text binary with distinct messages; text/PDF content is detected
regardless of extension. Readable but unimplemented layouts are preserved with
status `unsupported` and a visible explanation that no transactions were
imported. The last successful account selection is remembered in session.
Detectable identity mismatch currently uses authoritative prior receipts:
identical bytes already accepted for other named accounts show a warning and the
receipt keeps the newly selected account.

Carried requirement (not silently claimed): source-embedded identity — detecting
that a first-time statement belongs to a different account than the one selected
— cannot exist before a fixture-backed layout exposes an identity. It is tracked
as a required check in [ticket 05](05-import-lloyds-current-into-a-source-linked-transaction-view.md)
and must be re-verified there with Lloyds Current fixtures; tickets 07–09 repeat
it per family. P-03 identity fixtures are that work, not this ticket's.

Red: 12 of 28 tests failing/erroring (encrypted, corrupt, image-only, size, page
limits, content-over-extension, unsupported status, remembered selection,
mismatch).

Green: `.venv/bin/python manage.py test ledger` → 28 tests OK against real
PostgreSQL. `./scripts/smoke.sh` → exit 0, 28 tests, `restart check ok` (restart
fixture changed to a readable CSV); pypdf warnings for deliberately corrupt PDFs
are suppressed at logger level.

Browser demo: encrypted PDF → "This PDF is password-protected…"; CSV export →
receipt status "Unsupported" with the no-import explanation; reloading the form
preselected Lloyds Current; re-uploading the same CSV to Revolut Savings showed
"This file was previously accepted for Lloyds Current…" while the receipt stayed
with Revolut Savings.

Boundaries exercised: exactly 20 MiB accepted, 20 MiB + 1 rejected; 100 pages
accepted, 101 rejected. Rejected files leave no receipt and no stored blob.

Limits: local Mac evidence only; no supported layout yet, so every readable
upload is `unsupported`. Account-identity evidence inside statements is not yet
detected; only prior-receipt evidence is used, and never to reassign. Text/CSV
support is preservation-only until an explicit format contract exists. No push. Record red/green commands, behavioral demo, review findings/fixes,
local versus actual-host results, unresolved limits and commit reference when
available. Passing local tests alone cannot close a required real-host gate.
