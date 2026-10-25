# 21: Integrate bounded laptop wake and keep-awake leases

> Superseded execution task; not closed as complete. Status below is historical. Remaining work is owned by the [authoritative backlog](../../product-completion/ticket-plan.md).

Status: ready-for-agent
Claimed by: — (historical claim released at backlog cutover)
Approval: ticket breakdown approved by Sourav; private controller reuse approved 2026-10-22
Blocked by: P-06 target timing calibration and live integration approval (local implementation complete)
Parent: [First-release specification](../spec.md)
Acceptance trace: AC-18
Worker routing: Stronger implementation/design oversight and independent review recommended.

## What to build

Eligible work wakes the laptop through the existing controller and maintains only its own bounded active-work inhibition.

## Acceptance criteria

- [ ] Prepare private/local controller integration using its existing action-token mechanism without leaking tokens; obtain approval before live power/lease testing.
- [ ] Verify actual sleep-to-wake/readiness and create/extend/release/expiry paths, including failure/crash and the eight-hour creation-based ceiling.
- [x] Renew only legitimate active work, distinguish sleep lease from job ownership, and avoid accumulating excessive expiry through additive extensions.
- [ ] Release only application leases, never user leases or forced sleep; record actual-host evidence and retain local failure-contract tests.

## Test interface and verification

Infrastructure adapters plus actual controller/worker milestone. Use independently reviewed expected values and the approved
interfaces. For new behavioral code, observe a failing test and implement the minimum slice,
then repeat. Evaluation/evidence work runs the relevant existing checks; do not
create contrived tests of documentation. Include usable integration and meaningful
tests with the behavior rather than leaving a parser or UI stub. Follow [shared execution rules](../ticket-plan.md#execution-proposal)
for review, host evidence and permission limits.

## Prerequisites and scope limit

P-05 resolved for the existing private/local action-token path; P-06 cap-aware timing and live integration approval remain actual-host gates, not blockers to local adapter implementation.

No new controller service if the existing actions suffice; no uncontrolled sleep or power-loss test.

## Completion evidence

Local implementation, 2026-10-23:

- `jobs/controller.py` reads the controller page's rotating action token and
  sends `X-CSRF-Token` for `/api/wake` and power `create_lease`,
  `extend_lease`, `release_lease`. It refreshes once on 403, never logs the
  token, and maps malformed responses to typed controller errors.
- `KeepAwakeLease` (migration `jobs/0008`) owns one controller lease per worker
  attempt, separate from `JobAttempt` ownership. Claim starts it after commit;
  progress/heartbeat renew under a row lock only when 5 minutes remain; result
  and stale-attempt cleanup release after commit. Extension is capped by the
  controller's creation-plus-eight-hours limit.
- `LAPTOP_CONTROLLER_URL` is empty by default; the app does not wake or create
  leases without a configured private URL. Production Compose passes the URL
  and timing settings.
- The worker defaults to a one-shot drain and supports `--poll-interval` for the
  laptop container: drain, wait without a lease while idle, then check for newly
  released work while awake/resumed. User-run setup and a systemd startup unit
  are prepared, not installed. Actual wake and sleep/resume remain gated.
- Tests: `POSTGRES_DB=intellistore_wake_tdd_20261022 .venv/bin/python manage.py test jobs.tests.test_controller jobs.tests.test_keep_awake jobs.tests.test_readiness jobs.tests.test_scheduling`
  passed 40 tests. `./scripts/smoke.sh` passed Django checks, no migration
  drift, 253 tests, migrations and the two-process restart check, including a
  two-job worker drain and clean exit.
- Independent review found serialized-renewal and malformed-encoding defects;
  both were fixed with row locking and typed decode errors. Re-review found no
  findings. Tests cover rollback suppression and parallel renewal.
- Live read-only token parsing against `http://beng-mini-pc:8787` succeeded;
  no POST, wake, lease mutation, deployment or target database change occurred.
- Implementation commit: `dddf6d3` (not pushed).
- Setup preparation adds `compose.worker.yaml`, root-only runtime/token
  provisioning and both host scripts. Poll-after-idle TDD was observed failing
  before implementation; the 3 worker-process tests then passed. Full smoke now
  passes 254 tests. Real local app/DB-bind/worker containers completed HTTP
  upload → Process now → worker completion without a configured controller.
  Both ordinary hardening and the snap-compatible no-new-privileges=false
  selection were exercised locally; actual snap/AppArmor behavior remains a
  user-run host check. NAS backup work is not implemented.

Still open: actual sleep-to-wake, create/extend/release/expiry and inhibitor
behavior, failure/crash recovery, P-06 timing, container-to-controller
reachability, host worker service installation and actual-host acceptance.
Passing local tests cannot close those gates.

## Comments

2026-10-22: Sourav selected the existing controller-native scoped credential
path. Available source-backed notes establish session/CSRF only, so the
non-secret contract for issuance/scope, endpoint/header and rotation/revocation
is still needed. No token or controller request was sent; no controller code
change was authorized.

2026-10-22 (superseding the earlier credential request): Sourav authorized
read-only SSH to `beng-mini-pc` and inspection of the homepage at port 3000,
and selected reuse of that existing local mechanism. The homepage embeds the
controller on port 8787. Its GET-supplied process action token and
`X-CSRF-Token` header suffice for the existing wake and lease routes; no separate
scoped credential or controller change is required. Local adapter implementation
may proceed against this verified contract. Live power/lease actions and
deployment still require explicit approval.

2026-10-23: Local controller, keep-awake and worker-drain implementation
complete. No live POST or power/lease action was sent. Ticket remains open only
for P-06 timing, container reachability, host worker service, actual-host
lifecycle/failure evidence, and deployment approval.
