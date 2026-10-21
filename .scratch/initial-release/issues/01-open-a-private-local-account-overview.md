# 01: Open a private local account overview

Status: done
Claimed by: —
Blocked by: None
Parent: [First-release specification](../spec.md)
Acceptance trace: AC-01, AC-11
Worker routing: Stronger implementation/design oversight and independent review recommended.

## What to build

Sourav can sign in locally and see named account slots and an honest empty dashboard backed by real PostgreSQL.

## Acceptance criteria

- [x] Select and document the Mac test runtime before PostgreSQL-dependent tests; pin the initial compatible application/runtime dependencies.
- [x] Login gates the account overview; anonymous access is denied and no self-service registration exists.
- [x] Named account types include current, card and savings; empty balances are unknown, not fabricated zero history.
- [x] A fresh checkout can run the local smoke check with isolated storage; no existing host services or private data are touched.

## Test interface and verification

Application interfaces and browser journey. Use independently reviewed expected values and the approved
interfaces. For new behavioral code, observe a failing test and implement the minimum slice,
then repeat. Evaluation/evidence work runs the relevant existing checks; do not
create contrived tests of documentation. Include usable integration and meaningful
tests with the behavior rather than leaving a parser or UI stub. Follow [shared execution rules](../ticket-plan.md#execution-proposal)
for review, host evidence and permission limits.

## Prerequisites and scope limit

P-01, initial P-02; settle the local runtime choice explicitly before installation.

Do not build upload, worker, charts or production TLS yet. This foundation earns its scope through a running authenticated user journey.

## Completion evidence

Runtime: Sourav selected Docker Desktop on 2026-10-21. Installed Docker Desktop
4.96.0 (server 29.9.1, Compose v5.6.0); pinned Python 3.14, Django 6.1.2,
psycopg 3.2.13 and `postgres:17.11-alpine`. Recorded in ADR 0002, HLD section 5,
spec P-01 and README.

Red: `ledger/models.py` absent and `ledger:overview` unrouted —
`ImportError: No module named 'ledger.models'` (6 tests not collected).

Green: `.venv/bin/python manage.py test ledger -v 2` → 6 tests OK against real
PostgreSQL. `./scripts/smoke.sh` → check, `makemigrations --check`, 6 tests OK.

Behavioral demo: live `runserver` in Chromium — anonymous `/` redirected to
`/login/?next=/`; sign-in reached "Account overview" listing Lloyds Credit
(credit card), Lloyds Current (current account) and Revolut Savings (savings),
each "Balance unknown", with no `£0.00`.

Isolation: smoke runs under a per-invocation Compose project
(`beng-intellistore-smoke-<pid>`) on a free loopback port and removes only that
invocation's volume; verified the developer volume and its three accounts
survived a smoke run. No host services or private data touched.

Limits: local Mac evidence only; no deployment, TLS, phone layout or worker
behavior — later tickets. Fresh-checkout smoke still needs an installed Docker
Desktop daemon. No push.

Fresh checkout: `git clone --branch initial-release-integration` into an empty
directory ran `./scripts/smoke.sh` with exit 0, `Ran 6 tests`, `OK`.

Review (independent agent): no auth-gating, fabricated-balance or preservation
defect. Two must-fix findings, both docs/setup: (1) README recommended
`docker compose down --volumes`, which destroys the development database;
(2) `--keep` instructions implied chaining a dynamic smoke port into later
migrate/runserver commands. Fixed in README: development uses
`docker compose up -d --wait` on port 55432 and `docker compose down` keeps the
volume, with volume deletion labelled destructive. Also added a real
login-form test (wrong password rejected, correct password redirects to `/`)
and removed stale "runtime unverified" statements from ADR/HLD/spec.
