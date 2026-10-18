# 23: Complete phone and accessible browser journeys

Status: ready-for-agent
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

Not started. Record red/green commands, behavioral demo, review findings/fixes,
local versus actual-host results, unresolved limits and commit reference when
available. Passing local tests alone cannot close a required real-host gate.
