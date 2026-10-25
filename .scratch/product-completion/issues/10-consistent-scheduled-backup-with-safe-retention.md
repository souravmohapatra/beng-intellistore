# 10: Consistent scheduled backup with safe retention

Status: needs-info
Approval: task division approved by Sourav; planning/publication only.
Execution authorization: authorized; local implementation complete.
Blocked by: D3 destination/path approval and the user-run NAS exercise.
Draft reference: T12
Parent: [Authoritative completion specification](../spec.md)
Historical evidence: [24](../../initial-release/issues/24-create-consistent-backup-generations-with-visible-failure.md)

## What to deliver

Consistent scheduled backup with safe retention. Complete the end-to-end behavior below, reusing verified existing work rather than rebuilding it.

## Acceptance criteria

- [x] Consistent database + originals + corrections recovery generation while
  imports/edits continue; define the committed-state boundary before coding.
- [x] Run at 03:00 Europe/London; keep seven successful generations; retire an old
  generation only after a new complete success.
- [x] Interrupted/full/unavailable NAS and schedule/DST/catch-up failures are visible;
  no local deletion and no disruption of normal application use.
- [ ] Prove locally, then on approved NAS destination. Resolve path/headroom,
  consistency protocol and target permissions before the relevant implementation.

## Decision and external gates

D3: backup consistency method, verified NAS destination/capacity and target approval.
Read the [decision register](../spec.md#decision-register). A resolved decision does not authorize coding or live changes.

## Verification

Concurrent import/correction during backup, retention/interruption/storage-failure tests locally; then approved real NAS generation.

Follow [common completion rules](../spec.md#completion-rules): TDD for changed public behavior, runtime/browser proof, standards and spec review, and separate local/host evidence.

## Current evidence and completion

Local implementation and proof are complete; the real NAS run remains.

Consistency boundary (D3): `pg_dump --format=custom` provides the database
snapshot (including corrections and relationships). Accepted originals are
immutable and written before their database records, so copying originals after
the snapshot yields a superset containing every referenced original; unreferenced
extras are harmless. A generation is published only after a manifest hashes every
payload, `COMPLETE` is written, and the temporary directory is atomically renamed.

Implementation:
- `scripts/backup_generation.sh` runs inside the `backup` Compose service
  (`postgres:17.11-alpine`), reads originals read-only, writes to the NAS mount,
  records `backup.json` for the Status page, keeps seven complete generations and
  removes an older one only after the new generation completes.
- `deploy/systemd/intellistore-backup.{service,timer}` invoke Compose at 03:00
  Europe/London with `Persistent=true`; no project logic runs natively.
- Compose mounts the destination, originals and shared status directory with
  least privilege. Nothing is deployed.

Verification:
- `jobs.tests.test_backup_scripts`: 8 passing tests with controlled clients cover
  manifest publication, failed dump not counted, retention of seven, and failure
  never retiring a good generation.
- Real isolated proof (Docker Desktop, project `intellistore-ui-check`, PostgreSQL
  17.11 on port55487): ran the actual `postgres:17.11-alpine` backup container
  against the live isolated database while a writer committed corrections every
  ~20ms. The first generation restored with 3 of 122 corrections (a genuine
  mid-write snapshot); a second run maintained one active correction among 124
  rows. Restored `ledger_transaction`/`ledger_original`/`ledger_account` counts
  matched the source snapshot, both originals restored byte-identically, and the
  Status file recorded success.
- Concurrent imports/corrections continue during the read-only dump; local
  concurrency is additionally covered by task09's correction test.
- `docker compose -f compose.production.yaml config` validates with required envs
  and does *not* require NAS/restore settings; recovery services live in
  `compose.recovery.yaml` and are invoked explicitly.
- Actual committed Compose invocation was exercised under a scratch project:
  `docker compose -p recovery-smoke -f compose.production.yaml -f
  compose.recovery.yaml run --rm backup` created a complete generation and wrote
  `data/status/backup.json`; the matching `restore` service created and restored
  `smoke_restore` with exit0. The script mount is
  `${INTELLISTORE_COMPOSE_DIR}/scripts`, verified inside the service.

Remaining user-run steps (see `docs/runbooks/backup-restore.md`): set the approved
NAS path/status dir, confirm writable uid/headroom, install the timer, run one
controlled generation, and exercise an unavailable-destination failure. Those
close the NAS gate; they do not repeat the proven local protocol.
