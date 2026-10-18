# 02: Preserve an upload and reopen its original

Status: ready-for-agent
Approval: ticket breakdown approved by Sourav
Blocked by: 01
Parent: [First-release specification](../spec.md)
Acceptance trace: AC-02, AC-04, AC-19
Worker routing: Stronger implementation/design oversight and independent review recommended.

## What to build

A signed-in user can upload an original, receive a durable receipt, see it listed and reopen it after application restart.

## Acceptance criteria

- [ ] Original bytes and receipt/account association are preserved before successful acceptance.
- [ ] Inject failure between file/record steps and during storage-full/unavailable conditions; no false successful receipt or silent source loss.
- [ ] Restart retains accepted evidence; authenticated original retrieval returns the submitted bytes and anonymous retrieval is denied.
- [ ] Identical original bytes can reuse preserved evidence without erasing receipt history or silently changing account association.

## Test interface and verification

Application upload/original interfaces with real PostgreSQL and isolated files; browser smoke. Use independently reviewed expected values and the approved
interfaces. For new behavioral code, observe a failing test and implement the minimum slice,
then repeat. Evaluation/evidence work runs the relevant existing checks; do not
create contrived tests of documentation. Include usable integration and meaningful
tests with the behavior rather than leaving a parser or UI stub. Follow [shared execution rules](../ticket-plan.md#execution-proposal)
for review, host evidence and permission limits.

## Prerequisites and scope limit

P-02 original/record recovery contract; synthetic upload oracle.

No parser or NAS dependency. Verify restart behavior without claiming physical power-loss proof.

## Completion evidence

Not started. Record red/green commands, behavioral demo, review findings/fixes,
local versus actual-host results, unresolved limits and commit reference when
available. Passing local tests alone cannot close a required real-host gate.
