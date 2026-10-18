# 03: Explain intake rejection and account mismatches

Status: ready-for-agent
Approval: ticket breakdown approved by Sourav
Blocked by: 02
Parent: [First-release specification](../spec.md)
Acceptance trace: AC-02, AC-03
Worker routing: Budget worker candidate; stronger review required before completion.

## What to build

The upload flow explains rejected files, preserves readable unsupported layouts and flags source/account mismatches.

## Acceptance criteria

- [ ] Reject corrupt, password-protected and image-only inputs with distinct usable messages; enforce 20 MiB and 100 PDF pages including boundary cases.
- [ ] Check content rather than extension; readable unsupported formats remain preserved with explicit unsupported status and no financial-import success.
- [ ] Remember the selected named account and make detectable account identity mismatches visible without silent reassignment.
- [ ] Recognize only fixture-backed layouts; text/CSV acceptance does not imply arbitrary extraction support.

## Test interface and verification

Application intake interface and browser upload/status journey. Use independently reviewed expected values and the approved
interfaces. For new behavioral code, observe a failing test and implement the minimum slice,
then repeat. Evaluation/evidence work runs the relevant existing checks; do not
create contrived tests of documentation. Include usable integration and meaningful
tests with the behavior rather than leaving a parser or UI stub. Follow [shared execution rules](../ticket-plan.md#execution-proposal)
for review, host evidence and permission limits.

## Prerequisites and scope limit

P-03 safe rejection/identity fixtures.

No universal parser, password workflow or OCR.

## Completion evidence

Not started. Record red/green commands, behavioral demo, review findings/fixes,
local versus actual-host results, unresolved limits and commit reference when
available. Passing local tests alone cannot close a required real-host gate.
