# 02: Preserve an upload and reopen its original

Status: done
Claimed by: —
Blocked by: 01
Parent: [First-release specification](../spec.md)
Acceptance trace: AC-02, AC-04, AC-19
Worker routing: Stronger implementation/design oversight and independent review recommended.

## What to build

A signed-in user can upload an original, receive a durable receipt, see it listed and reopen it after application restart.

## Acceptance criteria

- [x] Original bytes and receipt/account association are preserved before successful acceptance.
- [x] Inject failure between file/record steps and during storage-full/unavailable conditions; no false successful receipt or silent source loss.
- [x] Restart retains accepted evidence; authenticated original retrieval returns the submitted bytes and anonymous retrieval is denied.
- [x] Identical original bytes can reuse preserved evidence without erasing receipt history or silently changing account association.

## Test interface and verification

Application upload/original interfaces with real PostgreSQL and isolated files; browser smoke. Use independently reviewed expected values and the approved
interfaces. For new behavioral code, observe a failing test and implement the minimum slice,
then repeat. Evaluation/evidence work runs the relevant existing checks; do not
create contrived tests of documentation. Include usable integration and meaningful
tests with the behavior rather than leaving a parser or UI stub. Follow [shared execution rules](../ticket-plan.md#execution-proposal)
for review, host evidence and permission limits.

## Prerequisites and scope limit

P-02 original/record recovery contract; synthetic upload oracle.

No parser or NAS dependency. Verify restart behavior without claiming physical power-loss proof.

## Completion evidence

Contract (P-02 originals): content-addressed blobs at
`INTELLISTORE_DATA_DIR/originals/<sha256[:2]>/<sha256>`, written to a same-directory
temporary file, fsynced, atomically renamed, then directory-fsynced. The blob is
stored before any receipt; `Original` and `Upload` are inserted in one
transaction. Receipts (`Upload`) carry the account, submitted filename and
status; identical bytes share one `Original` but never share a receipt.

Red: `ImportError: cannot import name 'Original' from 'ledger.models'`.

Green: `.venv/bin/python manage.py test ledger` → 14 tests OK (6 overview, 8
preservation) against real PostgreSQL and isolated temporary data directories.
`./scripts/smoke.sh` → exit 0: check, `makemigrations --check`, 14 tests,
`restart check ok`. Expected digest/size (`59353dc5…bd2f`, 83 bytes) were
established outside the application with `shasum -a 256` and `wc -c`.

Fault injection:
- Storage unavailable — the originals path is a real regular file, so `mkdir`
  fails: 503 "could not be preserved", no receipt, no `Original`.
- Failure between steps — a DB execute-wrapper raises on the `ledger_upload`
  insert: 503 "could not be recorded", no partial records (atomic), and the
  stored blob remains with exact fixture bytes, so nothing is silently lost.

Restart: `scripts/restart_check.py upload` and `verify` run in separate
interpreter processes against the same database and data directory; the second
process reopens the receipt and exact bytes. Also stopped and restarted the live
development server: the receipt stayed listed and `/uploads/1/original` still
returned `application/pdf`.

Browser demo: signed-in Chromium upload of a synthetic 83-byte PDF produced
`/uploads/1/` showing Lloyds Current, Pending, 83 bytes and the independently
known SHA-256; the original opened as PDF; anonymous GETs of the listing,
detail and original all redirect to login.

Note: uploading through the real UI initially hit the nav's sign-out button
because both are `button[type=submit]`; the upload form is now targeted by its
`enctype` form.

Limits: local Mac evidence only; no parser, job, limit enforcement (>20 MiB /
100 pages), content sniffing or account-mismatch handling — tickets 03+. Process
restart is not physical power-loss proof. No push.
