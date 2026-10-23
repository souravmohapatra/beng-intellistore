# Existing keep-awake contract

Read-only verification, 2026-10-18; rechecked 2026-10-22 by authorized SSH and browser GETs. No power or lease action was invoked.

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
not retained. A new API is not needed to express create/extend/release. Sourav
approved reusing this private/local controller mechanism on 2026-10-22 rather
than requiring a separate scoped machine credential.

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

## Verified local integration path (2026-10-22)

The live homepage at `http://beng-mini-pc:3000/` embeds the controller at
`http://192.168.68.55:8787/` as an iframe. Its `api/config/custom.js` changes
service links/themes, not wake/lease behavior. Browser inspection confirmed the
embedded controller URL and the controller's Wake/Keep awake controls; no button
was clicked. A read-only browser GET of `/api/capabilities` returned HTTP 200
and the power create/extend/release descriptors above.

Source inspected via authorized SSH:

- `controller/dashboard.py:9-17,26-32`: the page embeds `const csrf`, uses
  `X-CSRF-Token`, and posts JSON to `/api/action`. The Wake button posts to
  `/api/wake`; release supplies a lease ID; the manual extension adds 3600 seconds.
- `app.py:325-368,390-434`: GET `/` supplies the current process-generated action
  token. Every POST checks that header; no browser session cookie or separate
  machine login is required by these handlers. Wake returns 202; action success
  returns 200. Missing/stale token returns 403. Do not log or persist the token.
- `app.py:242-245`: request IDs match `[A-Za-z0-9._:-]{1,128}`.
- `controller/agent_client.py:99-127`: the controller forwards actions to the
  laptop over certificate-verified HTTPS with its own existing bearer credential.
  IntelliStore does not need that agent credential. Upstream action errors are
  returned; unavailable agent returns 503.
- `agent/leasing.py:266-344,382-454`: create/extend results contain
  `result.lease` with `lease_id`, ISO `created_at`/`expires_at`, and
  `remaining_seconds`; release contains `result.released`. The outer response
  includes `request_id`, `module`, and `action`. Unknown/expired lease is 404;
  a reused request ID with different parameters is 409. Successful identities
  are cached for only the latest 256 requests in that agent process.

The client can GET the controller page and extract its current action token
before POSTing the existing requests. A controller restart rotates the token;
403 must be distinguished from an ambiguous timeout after a lease mutation.
Do not blindly retry an ambiguous create/extend across agent restarts: request
identity caching is not durable.

`ssh beng-mini-pc "ss -ltn '( sport = :8787 )'"` showed listeners on loopback,
LAN and Tailscale addresses. The eventual app runs in Docker: container
`127.0.0.1` is not the mini-PC host. Configure a reachable private controller URL
and verify it from the deployed app container; do not assume host-gateway works
with the current address-specific listeners. No listener/network change was made.

The controller displayed Offline during inspection, with cached capabilities
and telemetry still visible. This establishes neither actual laptop state nor
worker readiness; the first authenticated IntelliStore worker claim remains the
readiness signal. Live wake/lease mutation, timing calibration and deployment
approval remain separate gates.


## Limits

Live GETs establish discoverability and advertised contract; source inspection
establishes intended implementation. Actual lease acquisition, renewal, release,
inhibitor permissions, restart restoration, sleep prevention and failure recovery
remain untested. No POSTs, wake/sleep calls, unit actions, installs or target
configuration changes were performed.
