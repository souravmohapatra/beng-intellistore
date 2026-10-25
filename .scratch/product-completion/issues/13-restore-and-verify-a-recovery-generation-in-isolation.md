# 13: Restore and verify a recovery generation in isolation

Status: needs-info
Approval: task division approved by Sourav; planning/publication only.
Execution authorization: authorized; local implementation and proofs complete.
Blocked by: [10](./10-consistent-scheduled-backup-with-safe-retention.md) (real NAS generation) and D3/D4 restore-target approval.
Draft reference: T13
Parent: [Authoritative completion specification](../spec.md)
Historical evidence: [25](../../initial-release/issues/25-restore-originals-records-and-corrections-into-isolation.md)

## What to deliver

Restore and verify a recovery generation in isolation. Complete the end-to-end behavior below, reusing verified existing work rather than rebuilding it.

## Acceptance criteria

- [x] Restore into a separate database/storage target; verify original bytes,
  evidence navigation, reports, mappings and confirmed corrections.
- [x] Reject incomplete/unusable generations and report measured recovery steps
  and recovery-window limits; never overwrite the live database for a test.
- [ ] Requires approval for actual NAS/host restore exercise and isolated capacity.

## Decision and external gates

D3/D4: isolated restore capacity and approved NAS/host exercise.
Read the [decision register](../spec.md#decision-register). A resolved decision does not authorize coding or live changes.

## Verification

Isolated restore from successful generation, byte comparisons and public evidence/report/correction checks; incomplete-generation rejection.

Follow [common completion rules](../spec.md#completion-rules): TDD for changed public behavior, runtime/browser proof, standards and spec review, and separate local/host evidence.

## Current evidence and completion

Local implementation and proof are complete; the actual host/NAS restore remains.

Implementation:
- `scripts/restore_generation.sh` runs in the `restore` Compose service. It
  requires a `COMPLETE` marker and verifies every manifest hash and size before
  writing, refuses to target the configured live database, refuses a non-empty
  originals target, restores the custom dump with `pg_restore`, and copies
  originals into the isolated directory.
- Compose mounts the backup destination read-only and an isolated restore
  directory; no live data path is writable.
- `docs/runbooks/backup-restore.md` records the user-run procedure, including
  public-surface checks for originals, reports, mappings and corrections.

Verification (controlled client binaries, real filesystem):
- `jobs.tests.test_backup_scripts` (8 restore tests): restores verified originals
  into an empty target; refuses the live database; rejects an incomplete
  generation; rejects empty/truncated manifests, unsafe paths, duplicate/omitted
  originals and tampered payloads before any psql/pg_restore call.
- Real isolated proof: restored a real generation (taken during concurrent
  correction writes) into `intellistore_restore_check3`. The restored database
  held 20 transactions, 184 of 222 corrections (a valid mid-write snapshot), 2
  originals and 2 accounts; both originals matched the manifest hashes. The
  application-level one-active-correction invariant is proven separately in
  `test_review_concurrency`; the direct-SQL writer used for load does not enforce
  it. A temporary app on
  port8030 pointed at the restored database/originals served overview, search,
  account, review and the original (`200`, `application/pdf`, exact bytes).
- A deliberately tampered generation is rejected before any write by the same
  manifest check proven in the tests.

Remaining user-run steps: confirm isolated capacity/permissions, restore a real
NAS generation, verify through a temporary app instance pointed at the restored
database/originals, record timings and recovery-window limits, then remove only
the temporary target.
