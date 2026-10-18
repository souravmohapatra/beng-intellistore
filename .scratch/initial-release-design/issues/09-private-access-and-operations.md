# Private access, batching, and operating policy

Type: grilling
Label: wayfinder:grilling
Status: resolved
Blocked by: 01, 05, 06, 08
Parent: [Initial release technical design](../map.md)

## Question

Choose private authentication and worker credentials, home/VPN routing and
transport, nightly schedule/timezone, acceptable wait, wake/readiness timeouts,
failure reporting, safe logs, and basic service lifecycle/backup cadence.
Retain OS-owned sleep and no external AI. Identify required deployment actions
for later approval rather than performing them in this decision session.

## Resolution evidence

Agreed operating policy and error behavior, with concrete defaults and remaining
configuration inputs; no secrets or unsupported availability claims.

## Evidence to consult

[Controller inventory](../research/host-storage-wake-inventory.md) records a
CSRF-protected HTML-client wake endpoint, not an established stable machine API.
Its 202 acknowledgement is not readiness; cached health is not worker health.
Tailscale installation does not imply an active Serve configuration or verified
application authentication. Resolve these contracts before integration.

## Confirmed first round

Sourav accepted Q48, Q49 and Q51; changed Q50 processing time to 21:00.

- Private HTTPS on home/VPN access, single Sourav login using Django's built-in
  authentication. No public exposure or self-service registration.
- Separate replaceable worker credential scoped to claiming jobs, assigned
  original downloads, progress reports and result submission; no login or DB
  credentials. Controller machine authentication still requires verification.
- Processing daily at 21:00 Europe/London; independent backup at 03:00 in the
  same timezone. Times are configurable. One catch-up run for each missed
  schedule after mini-PC downtime, rather than replaying every missed day.
  Backup captures consistent committed state without waiting indefinitely for
  laptop processing.
- Wake-to-application-worker-readiness deadline ten minutes, then visible
  unavailable state and queued work retained for manual retry or next batch.
  Avoid continuous wake attempts; startup deadline is not job execution timeout.
  Validate the deadline on actual hardware.

## Confirmed second round

Sourav accepted Q52-Q54:

- Failures stay visible in the application until resolved, with last successful
  processing and backup times. External notifications are deferred; Sourav must
  open the application to notice failures.
- Operational logs contain job identities, timings, stages and sanitized errors;
  exclude statement contents, transaction descriptions, account identifiers and
  credentials. Financial evidence remains in the protected application.
- Project containers restart automatically after crashes or host reboots and
  recover work through the agreed job rules. Upgrades, migrations and restores
  remain deliberate operations requiring approval when affecting existing data.

## Answer

Private HTTPS/home-VPN access with one Django login and a separate scoped worker
credential, 21:00 processing/03:00 independent backup in Europe/London, single
catch-up runs, a ten-minute readiness deadline, in-app failure reporting, safe
logs and automatic crash/reboot restart are accepted as detailed above.

The operating-policy decision is complete. Concrete hostname/certificates,
private routing, controller machine authentication, secret provisioning, runtime
versions, paths and exact probes must be specified and verified before deployment.
No credentials, installation, service changes or actual-host lifecycle tests were
performed. Schedule/DST/catch-up, readiness, failure visibility, log redaction and
restart recovery need acceptance tests; this resolution is policy, not proof of
working operations.
