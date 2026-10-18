# 10: Add savings mapping and independent account-section outcomes

Status: ready-for-agent
Approval: ticket breakdown approved by Sourav
Blocked by: 09
Parent: [First-release specification](../spec.md)
Acceptance trace: AC-02, AC-10, AC-11, AC-17
Worker routing: Stronger implementation/design oversight and independent review recommended.

## What to build

One Revolut upload populates personal GBP and savings GBP, preserving valid sections when another section fails validation.

## Acceptance criteria

- [ ] Confirm both section-to-named-account mappings on first import and reuse only with consistent source identity; never require PDF splitting.
- [ ] Publish supplied savings balance observations and explicit interest without inventing principal movements or complete daily history.
- [ ] Reconciliation failure retains that section's previous view while valid sections publish in one consistent update with visible partial status.
- [ ] Ignored joint/non-GBP/crypto sections cause no false coverage error; unexplained savings changes remain reviewable.

## Test interface and verification

Application mapping/result interfaces, interpretation and browser section status. Use independently reviewed expected values and the approved
interfaces. For new behavioral code, observe a failing test and implement the minimum slice,
then repeat. Evaluation/evidence work runs the relevant existing checks; do not
create contrived tests of documentation. Include usable integration and meaningful
tests with the behavior rather than leaving a parser or UI stub. Follow [shared execution rules](../ticket-plan.md#execution-proposal)
for review, host evidence and permission limits.

## Prerequisites and scope limit

P-02 section publication contract; P-03 savings fixture/oracle.

No transfer inference from missing savings principal rows.

## Completion evidence

Not started. Record red/green commands, behavioral demo, review findings/fixes,
local versus actual-host results, unresolved limits and commit reference when
available. Passing local tests alone cannot close a required real-host gate.
