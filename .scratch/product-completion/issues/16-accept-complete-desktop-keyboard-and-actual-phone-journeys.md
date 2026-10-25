# 16: Accept complete desktop, keyboard and actual-phone journeys

Status: needs-info
Approval: task division approved by Sourav; planning/publication only.
Execution authorization: authorized; local audits complete.
Blocked by: [08](./08-qualify-the-model-and-gate-enablement.md) (qualified advice), [12](./12-actionable-operational-status-without-private-logging.md), and D4 actual-phone/deployment acceptance.
Draft reference: T16
Parent: [Authoritative completion specification](../spec.md)
Historical evidence: [23](../../initial-release/issues/23-complete-phone-and-accessible-browser-journeys.md), [29](../../initial-release/issues/29-qualify-the-complete-deterministic-release-on-real-hosts.md)

## What to deliver

Accept complete desktop, keyboard and actual-phone journeys. Complete the end-to-end behavior below, reusing verified existing work rather than rebuilding it.

## Acceptance criteria

- [ ] Exercise onboarding, upload, dashboard, search, original access, corrections,
  qualified advice and failure/status journeys in the integrated application.
- [ ] Check labels, focus, errors, control targets and narrow layouts; include an
  actual phone, not only browser viewport emulation.
- [ ] Requires approved deployment and Sourav's actual-device acceptance; earlier
  local browser checks remain evidence, not a substitute.

## Decision and external gates

D4: integrated deployment approval and actual phone acceptance.
Read the [decision register](../spec.md#decision-register). A resolved decision does not authorize coding or live changes.

## Verification

Integrated desktop/keyboard/narrow viewport and actual-phone checklist; include qualified advice and unavailable dependencies.

Follow [common completion rules](../spec.md#completion-rules): TDD for changed public behavior, runtime/browser proof, standards and spec review, and separate local/host evidence.

## Current evidence and completion

Local desktop/keyboard/narrow audits are complete; qualified advice, actual phone
and deployed acceptance remain.

Local evidence (isolated app, real data):
- All eight surfaces (overview, uploads, upload receipt, search, review list,
  review detail, accounts, status) at390px: no document overflow; every visible
  input/select/textarea has a label; every button has an accessible name; exactly
  one h1; no image lacking alt; skip link present; active nav item marked.
- Keyboard: Tab reaches the brand link with a visible 3px focus outline and2px
  offset; tables render as labelled stacked rows (grid with `data-label` content).
- Earlier journeys in tasks01–04 exercised sign-in, account creation, upload,
  rejection, original access, corrections, advice request and status rendering.
- Automated suite:296 tests, including the concurrency and advice-fence cases.

Remaining user-run steps: exercise the same journeys on an actual phone over the
LAN, confirm qualified advice (task08) and failure/unavailable states in the
integrated deployment, and record device/browser/results. Viewport emulation is
not accepted as phone evidence.
