# Remaining deployment-environment checklist

Local implementation is complete for the tickets named below. These are the steps
that need the real machines, private data or your acceptance. Run them yourself
(or tell me when to run an approved subset); none is required for ordinary
browsing of already-imported data.

## 1. Laptop inference runtime (tasks05/06/08)

Follow `docs/runbooks/inference-runtime.md`:

1. Confirm NVIDIA container GPU access and free disk.
2. Start `compose.inference.yaml`, pull at most two candidates, record digests.
3. Obtain one real structured response from the worker container.
4. Request advice from a review item and confirm the suggestion appears end to
   end; confirm it changes nothing until you accept it.
5. Run `scripts/advice_benchmark.py` with at least 50 privately labelled cases;
   require `meets_gates: true` and a 100-item warm run inside ten minutes.
   Record cold-load time and GPU memory.
6. If no candidate passes, keep `INFERENCE_URL` empty; report the result for an
   explicit scope decision.

## 2. NAS backup and restore (tasks10/13)

Follow `docs/runbooks/backup-restore.md`:

1. Set `INTELLISTORE_BACKUP_DIR`, `INTELLISTORE_HOST_STATUS_DIR`,
   `INTELLISTORE_RESTORE_DIR`; confirm writable uid and headroom.
2. Install `intellistore-backup.service`/`.timer`; run one controlled generation.
3. Confirm the Status page shows success and seven-generation retention.
4. Make the destination unavailable once; confirm failure visibility, no local
   deletion, no good generation retired, and normal app use.
5. Restore the generation into a new database + empty originals directory; verify
   through a temporary app (dashboard, search, original bytes, corrections).
6. Record timings, counts, recovery window and limitations.

## 3. Real-host scheduling/wake (task11)

Within an approved window:

1. Verify the LAN deployment baseline and nightly 21:00 release + restart catch-up.
2. Confirm no wake for an empty queue and that Process now does not duplicate work.
3. Exercise wake → readiness → claim → lease → result → release, expiry and a
   failure path; confirm unrelated leases/services are untouched.
4. Record timings. Final combined parser+inference timing waits for task08.

## 4. Private statement acceptance (task14)

Provide the four representative originals and independent expected results
outsides Git. Run each through upload → worker → dashboard/search/review and
record exact discrepancies. Do not commit private files or expected values.

## 5. Performance measurement (task15)

On an isolated mini-PC benchmark copy:

```bash
python manage.py seed_benchmark_data --confirm-isolated
INTELLISTORE_BENCH_PASSWORD=... python scripts/latency_benchmark.py \
  --base-url http://<mini-pc>:8017 --username <user> --runs 30 \
  --output ~/private/latency-report.json
```

Require p95 ≤ 2s for dashboard, period, search, accounts and review; record cold
load, dataset/browser/network/runtime. Never seed the live database.

## 6. Phone and integrated acceptance (tasks16/17)

1. Use an actual phone over the LAN: sign in, create/select an account, upload,
   dashboard, search, open an original, confirm/revert a correction, request
   advice (if enabled), view status/failures.
2. Record device/browser/result and any layout problem.
3. Update `release-ledger.md` with host evidence, then accept or reject the
   release. Deployment and push remain separately authorized.

## Local verification snapshot

- `env POSTGRES_PORT=55487 .venv/bin/python manage.py test -v 0`:291 tests.
- Real isolated backup during concurrent writes; isolated restore verified through
  the application.
- No live host, private originals or push touched. Local changes are committed
  only on `initial-release-integration`.
