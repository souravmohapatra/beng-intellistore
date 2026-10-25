# 23: Complete phone and accessible browser journeys

> Superseded execution task; not closed as complete. Status below is historical. Remaining work is owned by the [authoritative backlog](../../product-completion/ticket-plan.md). UI work is paused and unaccepted.

Status: ready-for-agent
Claimed by: — (historical claim released at backlog cutover)
Approval: ticket breakdown approved by Sourav
Blocked by: 12, 13, 14
Parent: [First-release specification](../spec.md)
Acceptance trace: AC-11, AC-12, AC-13
Worker routing: Budget worker candidate; stronger review required before completion.

## What to build

Core dashboard, upload, search and one-at-a-time review work on narrow screens and desktop with clear visual hierarchy.

## Acceptance criteria

- [ ] Use stacked cards/forms rather than a desktop-width table requirement; preserve period/source/review navigation.
- [ ] Verify keyboard focus, labels, errors, status readability and usable controls for the core journeys.
- [ ] Respect the approved rendered UI/Chart.js stack and retain source/provisional/coverage distinctions while shaping visual design.
- [ ] Record automated desktop/narrow-viewport evidence and an actual phone smoke result; simulation alone is not phone verification.
- [ ] First-time users can create a named account in the application and continue to upload without Django admin; invalid/duplicate submissions preserve existing accounts.

## Test interface and verification

Browser journeys plus actual-phone acceptance at milestone. Use independently reviewed expected values and the approved
interfaces. For new behavioral code, observe a failing test and implement the minimum slice,
then repeat. Evaluation/evidence work runs the relevant existing checks; do not
create contrived tests of documentation. Include usable integration and meaningful
tests with the behavior rather than leaving a parser or UI stub. Follow [shared execution rules](../ticket-plan.md#execution-proposal)
for review, host evidence and permission limits.

## Prerequisites and scope limit

Existing working journeys; real phone availability for actual-device result.

Do not build a mobile app, redesign financial semantics or replace approved visual work during later fixes.

## Completion evidence

Production UI implementation remains incomplete. Sourav approved a visual
prototype checkpoint before full UI implementation, including first-run account
onboarding without routine Django-admin use.

Visual exploration is isolated on branch `prototype/product-ui`, worktree
`../beng-intellistore-ui-prototype`. Run `python3 scripts/ui_prototype.py`;
open `http://127.0.0.1:8027/?variant=A` (also B/C). Synthetic-only existing-route
previews avoid real authentication/data/mutations; no production routes changed.
Compare persistent overview, monthly brief and transaction-first workbench.
Onboarding, upload preview, review/confirmation, source dialog, search and failure
states are interactive in memory; no real inference or backup is represented.

Observed browser evidence: desktop screenshots of all three directions;390px
overview/review/empty layouts without page overflow; onboarding→upload→review,
confirmation/undo, advice-unavailable and worker-unavailable states, search/source
dialog, keyboard variant switching and reload-stable URLs. No browser errors.
This is visual-prototype evidence only, not actual-phone or production acceptance.
Sourav approved A's overview layout and the side-by-side source/decision Review
layout. Production implementation is now in progress against real Django data;
prototype values and simulated inference/backup states must not enter production.
