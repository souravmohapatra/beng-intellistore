# 16: Confirm repayments and own-account transfer links

Status: ready-for-agent
Approval: ticket breakdown approved by Sourav
Blocked by: 07, 08, 09, 14
Parent: [First-release specification](../spec.md)
Acceptance trace: AC-08, AC-10, AC-13
Worker routing: Stronger implementation/design oversight and independent review recommended.

## What to build

A user reviews and confirms supported transfer/repayment candidates while both account entries remain traceable and reporting avoids double counting.

## Acceptance criteria

- [ ] Candidate generation uses normalized evidence; equal/opposite amounts and nearby dates alone cannot prove ownership or pairing.
- [ ] Card purchase plus current-account repayment produces spending once and gross current-account outgoing once, with no repayment income.
- [ ] Other confirmed tracked-account transfers produce neither spending nor income; keep separate entries and both dates.
- [ ] Missing/ambiguous counterparts and excluded-account movements stay reviewable/provisional; never fabricate savings principal transactions.

## Test interface and verification

Application matching/review/report interfaces and browser paired-entry journey. Use independently reviewed expected values and the approved
interfaces. For new behavioral code, observe a failing test and implement the minimum slice,
then repeat. Evaluation/evidence work runs the relevant existing checks; do not
create contrived tests of documentation. Include usable integration and meaningful
tests with the behavior rather than leaving a parser or UI stub. Follow [shared execution rules](../ticket-plan.md#execution-proposal)
for review, host evidence and permission limits.

## Prerequisites and scope limit

P-03 independent paired/ambiguous/missing-counterpart fixtures.

Do not choose an unapproved automatic matching window to suppress review.

## Completion evidence

Not started. Record red/green commands, behavioral demo, review findings/fixes,
local versus actual-host results, unresolved limits and commit reference when
available. Passing local tests alone cannot close a required real-host gate.
