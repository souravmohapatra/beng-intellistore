# 20: Release nightly work and show Process now progress

> Historical completed work; not an active task. Preserve evidence below. Use the [authoritative backlog](../../product-completion/ticket-plan.md).

Status: done
Approval: ticket breakdown approved by Sourav
Blocked by: 04
Parent: [First-release specification](../spec.md)
Acceptance trace: AC-14, AC-20
Worker routing: Budget worker candidate; independent review and clean re-review completed.

## What to build

Uploads release at 21:00 Europe/London or Process now, with visible asynchronous status and safe restart catch-up.

## Acceptance criteria

- [x] Pending work remains ineligible just because the laptop is awake; an empty due queue sends no wake request.
- [x] Process now releases all waiting uploads without interrupting a job or duplicating work on repeat clicks.
- [x] One catch-up after a missed schedule, including DST/restart cases, does not replay every missed day.
- [x] Ten-minute wake-to-application-readiness deadline leaves unavailable work queued for manual retry/next batch. The first authenticated worker claim request is readiness; no separate endpoint, cached health, or controller acknowledgement counts.

## Test interface and verification

Application scheduling/job interfaces and browser status with controllable clock/controller. Use independently reviewed expected values and the approved
interfaces. For new behavioral code, observe a failing test and implement the minimum slice,
then repeat. Evaluation/evidence work runs the relevant existing checks; do not
create contrived tests of documentation. Include usable integration and meaningful
tests with the behavior rather than leaving a parser or UI stub. Follow [shared execution rules](../ticket-plan.md#execution-proposal)
for review, host evidence and permission limits.

## Prerequisites and scope limit

Readiness signal selected with Sourav: first authenticated worker claim; no separate health endpoint. Local clock/timezone fixtures exercise the ten-minute deadline. Sourav selected a mini-PC systemd timer as the trigger; local timer and Docker Compose configuration are prepared but not installed. Controller machine authentication/transport and actual-host behavior remain open for ticket 21.

Use controlled controller behavior locally; real wake/lease lifecycle belongs to the next slice.

## Completion evidence (2026-10-22)

- TDD red/green: the initial targeted suite failed two missing controller-call
  assertions. An expanded run failed four regressions for expired WAKING windows
  and outer-transaction rollback. The fixes refresh readiness before new release
  mutations and defer controller calls with `transaction.on_commit`; all 17
  targeted tests then passed. Independent re-review found no findings.
  ```sh
  POSTGRES_DB=intellistore_wake_tdd_20261022 .venv/bin/python manage.py test jobs.tests.test_scheduling jobs.tests.test_readiness
  POSTGRES_DB=intellistore_wake_tdd_20261022 .venv/bin/python manage.py test jobs.tests.test_readiness.WorkerReadinessTests.test_retry_requests_wake_once_after_valid_retry
  ```
- `./scripts/smoke.sh` passed: Django checks, no migration drift, 229 tests,
  migrations, and the two-process restart check.
- `WorkerWakeController` and `request_wake_for_released_work` provide a local
  injected boundary. The default `WORKER_WAKE_CONTROLLER = None` leaves batches
  queued; a configured controller is called only for eligible released work,
  after release transactions commit. Tests cover empty queues, nightly release,
  Process now, manual retry, and repeat requests.
- `release_due_jobs` passes 21:00 Europe/London, coalesced catch-up, and spring
  DST tests; the restart check proves its persisted cursor is not replayed.
- The first authenticated worker claim confirms readiness; deadline expiry
  requeues work. Signed-in Chromium on the isolated app showed unavailable work
  retained in the queue.
- Mini-PC systemd/production Compose config was validated locally in isolated
  containers; no unit was installed, no target database was migrated, and no
  host was contacted.
- Still open under ticket 21: machine authentication, real wake/lease lifecycle,
  and worker drain. Ticket 06 retains host timer/daemon/clock and deployment
  acceptance. No live controller request was sent.

## Comments

2026-10-22: Sourav selected the first authenticated worker claim request as the
application-readiness signal. No dedicated readiness endpoint is required.
