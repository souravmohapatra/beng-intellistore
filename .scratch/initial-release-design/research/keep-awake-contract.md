# Existing keep-awake contract

Read-only verification, 2026-10-18. No power or lease action was invoked.

## Observed interface

`GET http://127.0.0.1:8787/` through `beng-mini-pc` returned HTTP 200 and the
Keep awake section. `GET /api/capabilities` returned the Power module with:

| Action | Parameters | Documented/advertised limits |
| --- | --- | --- |
| `create_lease` | `duration_seconds` | Integer 1–28800 seconds; default 3600. |
| `extend_lease` | `lease_id`, `extension_seconds` | Integer extension 1–28800 seconds. |
| `release_lease` | `lease_id` | Required nonempty string. |

The UI uses `POST /api/action` with `module: power`, the action name, parameters
and a request identity, plus the page's `X-CSRF-Token`. Source also exposes
module-specific action paths. Token values and current lease identities were
not retained. A new API is not needed to express create/extend/release, though
machine-client authentication remains an integration decision.

## Source-backed semantics

Inspected under `/opt/beng-laptop-controller/source/` on the mini-PC:

- `controller/dashboard.py`: existing generic action helper and controls.
- `agent/modules/power.py`: action descriptor and parameter limits.
- `agent/leasing.py`: create, extend, remove, persistence, expiry and inhibitor.
- `app.py`: controller forwarding for `/api/action`.

Lease creation starts `systemd-inhibit --what=idle:sleep --mode=block` around a
bounded sleep process and returns the lease identity/expiry. The manager persists
leases and expires them. Release removes the matching inhibitor; it does not
command laptop sleep. Agent restart restoration is implemented in source, not
tested by this investigation.

Extension is additive to the current expiry and capped at creation time plus
eight hours, not eight hours from each renewal. At the ceiling it returns an
error. The worker adapter must use short bounded durations, renew based on
remaining lifetime, and handle the ceiling explicitly; blindly adding duration
on every heartbeat could unnecessarily prolong inhibition after a worker crash.
Execution timeouts and job ownership remain separate controls.

Keep-awake leases and application job claims are distinct. The former blocks
idle/sleep while active work runs; the latter authorizes a result to publish.
Neither cached controller health nor a sleep inhibitor proves worker readiness
or continued job ownership. Release only the application's own lease, leaving
manual/user leases intact. Stop renewing when the worker no longer owns work.

Action-dispatch request identities have bounded process-local caching in the
inspected source, not a durable exactly-once guarantee across restarts. Do not
substitute this for application-side job/attempt and result idempotency.

## Limits

Live GETs establish discoverability and advertised contract; source inspection
establishes intended implementation. Actual lease acquisition, renewal, release,
inhibitor permissions, restart restoration, sleep prevention and failure recovery
remain untested. No POSTs, wake/sleep calls, unit actions, installs or target
configuration changes were performed.
