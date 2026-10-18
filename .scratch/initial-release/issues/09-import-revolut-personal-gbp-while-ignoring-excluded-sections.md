# 09: Import Revolut personal GBP while ignoring excluded sections

Status: ready-for-agent
Approval: ticket breakdown approved by Sourav
Blocked by: 05
Parent: [First-release specification](../spec.md)
Acceptance trace: AC-02, AC-05, AC-10
Worker routing: Budget worker candidate; stronger review required before completion.

## What to build

A consolidated Revolut original imports personal GBP rows and balances while clearly ignoring joint, non-GBP and crypto sections.

## Acceptance criteria

- [ ] Synthetic consolidated fixture includes supported and excluded sections, wrapped rows and repeated summaries; only personal GBP is imported in this slice.
- [ ] Retain signed native GBP values, account identity and running balance evidence; GBP equivalents from excluded currencies never create GBP transactions.
- [ ] Source original remains unchanged and accessible, with included/excluded sections understandable in processing status.
- [ ] Unclear GBP movements to excluded accounts remain reviewable rather than silently confirmed spending or income.

## Test interface and verification

Statement interpretation and application mapping/publication/browser views. Use independently reviewed expected values and the approved
interfaces. For new behavioral code, observe a failing test and implement the minimum slice,
then repeat. Evaluation/evidence work runs the relevant existing checks; do not
create contrived tests of documentation. Include usable integration and meaningful
tests with the behavior rather than leaving a parser or UI stub. Follow [shared execution rules](../ticket-plan.md#execution-proposal)
for review, host evidence and permission limits.

## Prerequisites and scope limit

P-03 consolidated Revolut fixture; mapping must distinguish included personal GBP from excluded joint GBP.

Savings is explicitly not supported until the next slice; no false complete outcome when that supported-release section still awaits implementation.

## Completion evidence

Not started. Record red/green commands, behavioral demo, review findings/fixes,
local versus actual-host results, unresolved limits and commit reference when
available. Passing local tests alone cannot close a required real-host gate.
