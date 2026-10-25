# 15: Measure and meet real-host dashboard/search latency

Status: needs-info
Approval: task division approved by Sourav; planning/publication only.
Execution authorization: authorized; local harness ready.
Blocked by: [02](./02-evidence-first-dashboard-and-transaction-navigation.md) and D4 isolated mini-PC benchmark approval.
Draft reference: T15
Parent: [Authoritative completion specification](../spec.md)
Historical evidence: [26](../../initial-release/issues/26-measure-and-meet-dashboard-and-search-latency.md)

## What to deliver

Measure and meet real-host dashboard/search latency. Complete the end-to-end behavior below, reusing verified existing work rather than rebuilding it.

## Acceptance criteria

- [ ] On an approved isolated mini-PC deployment, use 100,000 synthetic transactions
  spanning up to ten years; at least 30 warm repetitions per representative
  dashboard/period/search journey, p95 at most two seconds.
- [x] Report cold first load, dataset/query/browser/network/runtime conditions;
  optimize and repeat only where needed. Never seed benchmark data into live DB.
- [ ] Requires an actual-host deployment baseline and resource approval; does not
  wait for unrelated wake/backup work.

## Decision and external gates

D4: isolated mini-PC benchmark deployment and resource approval.
Read the [decision register](../spec.md#decision-register). A resolved decision does not authorize coding or live changes.

## Verification

Actual mini-PC browser end-to-end latency report: cold load plus at least30 warm repetitions per journey, p95 and conditions.

Follow [common completion rules](../spec.md#completion-rules): TDD for changed public behavior, runtime/browser proof, standards and spec review, and separate local/host evidence.

## Current evidence and completion

Local harness is ready; actual mini-PC measurement remains.

Implementation:
- `jobs/management/commands/seed_benchmark_data.py` seeds 100,000 synthetic
  transactions across ten years into a named isolated database. It refuses
  without `--confirm-isolated` and refuses the configured live database name.
- `scripts/latency_benchmark.py` is an HTTP diagnostic only (server response
  time), explicitly labelled `mode: http-diagnostic`; it is not the release gate.
- `scripts/browser_latency_benchmark.py` (optional `requirements-benchmark.txt`)
  measures submission-to-visible in Chromium for dashboard, period submit, search
  and review, cold + 30 warm repetitions, p50/p95/max and the 2-second verdict.

Verification:
- Seeder tests: confirmation required, live-database refusal, one-time seeding
  (50 transactions, 2 balance anchors).
- HTTP diagnostic smoke (small dataset, not acceptance): p95 max 26.5ms.
- Browser harness smoke against the isolated app: dashboard 40.6ms, period
  122–131ms, search 99–101ms, review 53ms p95 over 3 runs; JSON
  `mode: browser-submit-to-visible`, `meets_two_seconds: true`. Small synthetic
  data and a Mac, so this validates the harness only.
- Playwright is pinned in `requirements-benchmark.txt`; no runtime dependency was
  added to the application requirements.
- No live data was seeded; the command guard is tested.

Remaining user-run steps: deploy the benchmark copy on the mini-PC, seed 100,000
rows there, run at least 30 warm repetitions per journey over the home LAN,
record cold load/browser/runtime/network, and attach the JSON report. Optimize
only if p95 exceeds two seconds.
