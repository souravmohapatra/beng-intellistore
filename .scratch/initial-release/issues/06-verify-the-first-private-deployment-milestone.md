# 06: Verify the first private deployment milestone

Status: ready-for-agent
Approval: ticket breakdown approved by Sourav
Blocked by: 05
Parent: [First-release specification](../spec.md)
Acceptance trace: AC-01, AC-04, AC-05, AC-19
Worker routing: Stronger implementation/design oversight and independent review recommended.

## What to build

An isolated project deployment on the actual mini-PC/laptop can privately upload and process a Lloyds Current statement and reopen its evidence.

## Acceptance criteria

- [ ] Prepare reviewable deployment configuration and runbook before seeking deployment approval; obtain local data paths and inspect actual Docker endpoint, capacity and storage behavior.
- [ ] Verify private hostname/TLS/home-VPN routing and scoped worker connectivity; do not reuse or modify vendor databases or unrelated services.
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

## Completion evidence

Not started. Record red/green commands, behavioral demo, review findings/fixes,
local versus actual-host results, unresolved limits and commit reference when
available. Passing local tests alone cannot close a required real-host gate.
