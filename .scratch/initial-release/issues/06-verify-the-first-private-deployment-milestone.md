# 06: Verify the first private deployment milestone

> Superseded execution task; not closed as complete. Status below is historical. Remaining work is owned by the [authoritative backlog](../../product-completion/ticket-plan.md).

Status: needs-info
Approval: ticket breakdown approved by Sourav
Blocked by: 05
Parent: [First-release specification](../spec.md)
Acceptance trace: AC-01, AC-04, AC-05, AC-19
Worker routing: Stronger implementation/design oversight and independent review recommended.

## What to build

An isolated project deployment on the actual mini-PC/laptop can privately upload and process a Lloyds Current statement and reopen its evidence.

## Acceptance criteria

- [ ] Prepare reviewable deployment configuration and runbook before seeking deployment approval; obtain local data paths and inspect actual Docker endpoint, capacity and storage behavior.
- [ ] Verify the selected LAN-only direct HTTP/DNS access and scoped worker connectivity; TLS/reverse proxy/VPN are deferred by Sourav for this deployment. Do not reuse or modify vendor databases or unrelated services.
- [ ] After authorized deployment, verify real source against a private independent oracle and prove ordinary committed browsing does not require laptop/NAS availability.
- [ ] Record actual host evidence, rollback/restart procedure and remaining release gates; this is a milestone, not production release or push approval.

## Test interface and verification

Infrastructure operational interfaces plus actual-host browser/application journey. Use independently reviewed expected values and the approved
interfaces. For new behavioral code, observe a failing test and implement the minimum slice,
then repeat. Evaluation/evidence work runs the relevant existing checks; do not
create contrived tests of documentation. Include usable integration and meaningful
tests with the behavior rather than leaving a parser or UI stub. Follow [shared execution rules](../ticket-plan.md#execution-proposal)
for review, host evidence and permission limits.

## Prerequisites and scope limit

P-04, P-05, explicit approval for deployment; host/path inputs.

No real power/lease/model actions or NAS database. Existing native Ollama does not select project deployment policy.

## Comments

### 2026-10-21 — Sourav: continue implementation while deployment is deferred

Ticket 06 gates actual deployment and its real-host acceptance only; it is not
a stop gate for the implementation backlog. Keep this ticket `needs-info` and
continue the lowest available ticket whose declared blockers are done. Do not
stop or repeatedly request deployment approval merely because 06 is unresolved.

Continue local implementation, tests, deployment configuration and runbook
preparation now. At this checkpoint, finish the existing ticket-18 recovery work
and its failing test, then continue other available tickets in dependency order.
For host-dependent tickets, complete useful local preparation and record the
remaining host checks without claiming those checks passed or closing the ticket.
Preserve explicit dependencies on 06 (including 26 and 28).

Only deploying to the actual machines or migrations affecting existing data
requires the corresponding explicit approval; deployment configuration also
needs the paths, private access and authentication inputs listed above. Prepare
a concrete reviewable configuration/runbook before requesting deployment approval.
This instruction authorizes continued implementation, not deployment, destructive
operations, migrations affecting existing data, or Git push.

## Completion evidence

Local deployment configuration is prepared but this ticket remains `needs-info`
and no real-host acceptance is claimed:

- Added `Dockerfile`, `.dockerignore`, `compose.production.yaml`, systemd service
  and timer units, and README setup/verification instructions.
- Local production Compose validation/build passed; an isolated database
  migrated, the app became healthy and rendered the login page, and the release
  command ran against the same temporary database. Temporary volumes were
  removed.
- `systemd-analyze verify` and Europe/London calendar parsing passed in a
  disposable Debian container. `./scripts/smoke.sh` passed with 222 tests and
  the two-process restart check.

Current deployment inputs: Sourav selected `/mnt/media/intelli-store` on the
mini-PC and LAN-only direct HTTP without proxy/TLS. Read-only SSH verified the
empty UID/GID1000 directory on local ext4, about257GiB free, and the explicit
Docker socket `/var/run/docker.sock` serving the snap daemon. Port8017 is unused
at inspection; scripts recheck before publishing192.168.68.55:8017. The database
and originals get dedicated `postgres/` and `data/` bind paths.

User-run `beng-mini-pc-setup.sh` and `beng-laptop-setup.sh` now prepare both hosts,
with local secret generation, login/worker credential provisioning and startup
units. Laptop SSH timed out; prerequisites are checked by its local script.
No installation, target migration, firewall/proxy change or power/lease POST
was performed. NAS destination/backups, target timing and actual-host evidence
remain open. Source/controller authentication is no longer a blocker.

Setup verification: shell syntax and help paths pass; ShellCheck v0.11.0 passes
with SC1087 excluded for the unchanged upstream wizard library. Boundary/secret
preservation checks and both Compose runtime configurations pass. Disposable Linux
systemd verification and the London calendar parse pass. Actual local production
app/PostgreSQL-bind/worker containers completed a synthetic HTTP upload and
Process now flow using the non-root worker; originals remained in the bind path.
Full `./scripts/smoke.sh`: 254 tests, checks, migrations and restart check pass.

Additional permission found: Docker snap's `removable-media` plug is disconnected.
Setup offers an explicit `snap connect docker:removable-media` consent for
`/mnt/media`. Canonical documents its no-new-privileges/AppArmor incompatibility;
setup uses the same false setting as existing mini-PC containers, retaining
non-root/read-only/drop-all-capabilities app and worker restrictions. No plug,
daemon setting, container or host service was changed during inspection.

Two independent read-only reviews found no qualifying introduced defects.
Their residual risks were addressed locally: release now requires/orders after
the app startup service, and declining timer activation reports an existing
active/enabled timer accurately instead of claiming it was disabled.
