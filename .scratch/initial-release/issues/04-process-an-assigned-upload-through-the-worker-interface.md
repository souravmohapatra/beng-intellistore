# 04: Process an assigned upload through the worker interface

> Historical completed work; not an active task. Preserve evidence below. Use the [authoritative backlog](../../product-completion/ticket-plan.md).

Status: done
Claimed by: —
Approval: ticket breakdown approved by Sourav
Blocked by: 03
Parent: [First-release specification](../spec.md)
Acceptance trace: AC-01, AC-06, AC-14, AC-15, AC-17
Worker routing: Stronger implementation/design oversight and independent review recommended.

## What to build

Process now releases a waiting upload to one worker, which downloads its assigned source and returns a visible validated outcome through the application.

## Acceptance criteria

- [x] Pending work is not claimable merely because a worker is awake; explicit Process now releases waiting uploads without interruption or duplicate effects.
- [x] A separate replaceable scoped credential permits claims, assigned source reads, progress and result submission only; user/DB privileges and unrelated originals are denied.
- [x] One active worker job initially; define minimal versioned result/attempt and section-evidence contracts without inventing the complete future schema.
- [x] An unsupported-source outcome is returned and visible without financial effects; normal completion cleans worker temporary files and records basic progress.
- [x] Never expose a half-committed result as complete; basic repeated submission cannot add financial effects. Later recovery tickets harden the adversarial paths.

## Test interface and verification

Application job/result interfaces with real PostgreSQL/files and a controlled external worker. Use independently reviewed expected values and the approved
interfaces. For new behavioral code, observe a failing test and implement the minimum slice,
then repeat. Evaluation/evidence work runs the relevant existing checks; do not
create contrived tests of documentation. Include usable integration and meaningful
tests with the behavior rather than leaving a parser or UI stub. Follow [shared execution rules](../ticket-plan.md#execution-proposal)
for review, host evidence and permission limits.

## Prerequisites and scope limit

P-02 job/result contracts and credential provisioning for local tests.

No scheduled release, real wake calls or model inference. Use the unsupported result as the first real round trip, not a fabricated bank transaction.

## Completion evidence

Contracts: one upload = one `Job`; uploads create a `waiting` job atomically with
the receipt. `jobs/api.py` exposes `POST /api/worker/claims/`,
`GET /api/worker/jobs/<id>/source/`, `POST …/progress/` and `POST …/result/`
behind a replaceable bearer credential (`WorkerCredential`, sha256 token hash,
`provision_worker` prints it once). Result payload version 1 carries `attempt`,
`outcome`, `issues`, `sections`; unsupported and failed are the only enabled
outcomes until a parser exists. `Process now` releases every waiting job and is
idempotent.

Red: 13 new tests failed (missing `jobs` app/API and worker module).

Green: `.venv/bin/python manage.py test` → 42 tests OK against real PostgreSQL.
`./scripts/smoke.sh` → exit 0, 42 tests, `restart check ok`.

Concurrency: `claim` takes a PostgreSQL transaction advisory lock
(`pg_advisory_xact_lock`) before deciding, because row locks do not serialize the
empty-`PROCESSING` case. A barrier test starts two simultaneous claims and
asserts exactly one 200, one 204 and one processing job; I confirmed it fails
when the lock call is removed, so the test is sensitive.

Fault/invariant coverage: waiting jobs are unclaimable; repeated release does not
duplicate attempts; a second claim while processing returns 204 and succeeds
after the first result; source reads are denied to another credential (403) and
unclaimed jobs (409); progress is recorded and shown; identical resubmission
returns `already_recorded` with one recorded result; a conflicting payload for
the same attempt returns 409; unknown version/outcome returns 400; results commit
atomically with attempt completion and job status.

Live Mac demo: uploaded CSV receipts, clicked Process now (3 waiting → 0
waiting), ran `python -m worker` three times against `runserver` — jobs 1–3
completed, then `no work`; `/tmp/worker-root` stayed empty; receipt shows Job
Completed, Attempt 1 by dev-laptop, `downloaded`, `inspected`, Outcome
unsupported and the `unsupported_layout` issue.

Limits: local Mac evidence only; no scheduling, wake, heartbeat/expiry, retries
or stale fencing (tickets 18–21); one real worker process; no parser, so every
outcome is `unsupported`. No deployment or push. Record red/green commands, behavioral demo, review findings/fixes,
local versus actual-host results, unresolved limits and commit reference when
available. Passing local tests alone cannot close a required real-host gate.
