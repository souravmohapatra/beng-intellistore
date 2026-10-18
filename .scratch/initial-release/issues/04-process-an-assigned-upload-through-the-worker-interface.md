# 04: Process an assigned upload through the worker interface

Status: ready-for-agent
Approval: ticket breakdown approved by Sourav
Blocked by: 03
Parent: [First-release specification](../spec.md)
Acceptance trace: AC-01, AC-06, AC-14, AC-15, AC-17
Worker routing: Stronger implementation/design oversight and independent review recommended.

## What to build

Process now releases a waiting upload to one worker, which downloads its assigned source and returns a visible validated outcome through the application.

## Acceptance criteria

- [ ] Pending work is not claimable merely because a worker is awake; explicit Process now releases waiting uploads without interruption or duplicate effects.
- [ ] A separate replaceable scoped credential permits claims, assigned source reads, progress and result submission only; user/DB privileges and unrelated originals are denied.
- [ ] One active worker job initially; define minimal versioned result/attempt and section-evidence contracts without inventing the complete future schema.
- [ ] An unsupported-source outcome is returned and visible without financial effects; normal completion cleans worker temporary files and records basic progress.
- [ ] Never expose a half-committed result as complete; basic repeated submission cannot add financial effects. Later recovery tickets harden the adversarial paths.

## Test interface and verification

Application job/result interfaces with real PostgreSQL/files and a controlled external worker. Use independently reviewed expected values and the approved
interfaces. For new behavioral code, observe a failing test and implement the minimum slice,
then repeat. Evaluation/evidence work runs the relevant existing checks; do not
create contrived tests of documentation. Include usable integration and meaningful
tests with the behavior rather than leaving a parser or UI stub. Follow [shared execution rules](../ticket-plan.md#execution-proposal)
for review, host evidence and permission limits.

## Prerequisites and scope limit

P-02 job/result contracts and credential provisioning for local tests.

No scheduled release, real wake calls or model inference. Use the unsupported result as the first real round trip, not a fabricated bank transaction.

## Completion evidence

Not started. Record red/green commands, behavioral demo, review findings/fixes,
local versus actual-host results, unresolved limits and commit reference when
available. Passing local tests alone cannot close a required real-host gate.
