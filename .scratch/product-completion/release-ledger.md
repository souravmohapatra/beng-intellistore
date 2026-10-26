# Release evidence ledger

This ledger records the current disposition of each applicable acceptance
criterion. Local evidence is not host evidence; an unchecked host/device gate
keeps the item open. Task17 closes only when every row is accepted.

Legend: **local** = exercised on this Mac against isolated PostgreSQL/files and
the real application; **host** = requires the approved mini-PC/laptop/NAS
deployment; **user** = requires Sourav's private files, device or decision.

| AC | Disposition | Evidence / remaining gate |
| --- | --- | --- |
| AC-01 | local pass; host open | Authenticated routing, worker bearer scoping and unauthenticated redirects tested; deployed LAN login is a task11/16 host check. |
| AC-02 | local pass; host open | Onboarding/mapping/mismatch tests pass; all four supplied originals uploaded with named-account assignments in the isolated local UI. |
| AC-03 | local pass | Rejection, unsupported preservation and clear messages tested in intake suites. |
| AC-04 | local pass | Receipt survives restart tests; storage/receipt failures report 503 without success. |
| AC-05 | local source proof; full oracle open | All four supplied PDFs import and reconcile; Current17/Credit78/Amex13/Revolut10 match prior source inventory. Independently established full-field and edge-case acceptance remains Task14. |
| AC-06 | local pass | Lost-ack replay, conflicting payload rejection and duplicate suppression tested. |
| AC-07 | local pass | Overlap candidates retain both rows; confirmed duplicates suppress one effect only. |
| AC-08 | local pass | Transfer/repayment link tests retain both entries with agreed effects. |
| AC-09 | local pass | Refund/cash-withdrawal/fee effects covered by reporting and review tests. |
| AC-10 | local pass | Revolut personal/savings GBP, exclusions, conversions and partial sections tested. |
| AC-11 | local pass; host open | Dashboard totals, unknown/missing/disputed states and coverage gaps tested and browser-verified. |
| AC-12 | local pass; user open | Search/drilldown retain period and reach originals; actual phone remains task16. |
| AC-13 | local pass | Correction history/revert, concurrent corrections and mapping mismatch tested. |
| AC-14 | local pass; host open | Release/Process-now/no-wake/duplicate-click behavior tested; real 21:00 timing is task11. |
| AC-15 | local pass; host open | Worker uses scoped API only; temp cleanup tested; deployed run is task11. |
| AC-16 | local pass; host open | Expiry, bounded retries, review failure and interruption tested; power scenarios in task11. |
| AC-17 | local pass | Partial-section publication, failed-section retention and reconciliation gates tested. |
| AC-18 | local pass; host open | Lease create/renew/release/expiry and ceiling tested; actual wake/lease lifecycle in task11. |
| AC-19 | local pass; host open | Normal use independent of laptop/NAS tested; NAS failure visibility in task10/12. |
| AC-20 | local pass; host open | Restart catch-up during one run tested; timezone/DST host evidence in task11. |
| AC-21 | local proof; host open | Real container backup during concurrent writes, retention and failure safety tested; NAS generation is task10 user run. |
| AC-22 | local proof; host open | Real generation restored to an isolated PostgreSQL and verified through the app; NAS restore remains task13 user run. |
| AC-23 | local pass; host open | Status page shows last success/failure and actions; logs contain no contents. Real deployment logs in task11. |
| AC-24 | local pass | History older than twelve months remains queryable; no purge/archival path exists. |
| AC-25 | local pass; real runtime open | Advice is validated, source-linked and confirmation-only; unavailable runtime leaves imports/review usable. The real-model demonstration and enablement gate remain task05/06/08. |
| AC-26 | harness ready; user open | Evaluation harness and gates implemented; private labels and actual-laptop run remain task08. |
| AC-27 | local100k pass; host open | Chromium30-warm p95: dashboard1020.8ms, period266.1ms, search126.6ms on the Mac/loopback. Actual mini-PC/LAN qualification remains Task15. |

## Latest integrated local verification —2026-10-26

- `./scripts/smoke.sh`:377tests pass, Django check/no migration drift, fresh
  PostgreSQL migrations, restart proof and owned scratch cleanup pass.
- Supplied originals exercised through browser intake→real worker API→
  dashboard/drilldown/search/review; all four original downloads are byte-exact.
  Amex summary-box and Lloyds Credit source-layout defects fixed with sanitized
  tests. No private source contents or monetary values committed.
- Real backup/isolated restore retained20transactions,222corrections and
 2originals; restored app source bytes matched its manifest. A read-only
  destination produced a failed attempt without erasing last success.
- Independent financial/advisory and recovery/measurement reviewers checked
  changes and their revisions; no remaining findings in the reviewed slices.
- SSH inventory only: mini-PC revision`079e96d`, app/release timer active, backup
  timer inactive; laptop worker active, inference port11435 not listening.
  Mini-PC non-interactive sudo requires a password. No target mutation, model
  download, power exercise or push performed.
- Verified local commits: `4dcde91` (supplied formats/refunds), `42eff66`
  (advisory qualification/review/status), `44a8c5d` (recovery/setup safety).
  After the full smoke, fixture identifiers/comments were sanitized before
  committing; the focused Amex/Lloyds Credit 36-test run also passes.

## Operating handoff

- Inference runtime: `docs/runbooks/inference-runtime.md`
- Backup and isolated restore: `docs/runbooks/backup-restore.md`
- Deployment setup scripts/units: `deploy/`, `compose.production.yaml`,
  `compose.worker.yaml`, `compose.inference.yaml`
- Release acceptance remains open until the host/user gates above are recorded
  with commands, results and limitations.
