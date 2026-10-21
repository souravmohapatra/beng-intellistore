# 16: Confirm repayments and own-account transfer links

Status: done
Approval: ticket breakdown approved by Sourav
Blocked by: 07, 08, 09, 14
Parent: [First-release specification](../spec.md)
Acceptance trace: AC-08, AC-10, AC-13
Worker routing: Stronger implementation/design oversight and independent review recommended.

## What to build

A user reviews and confirms supported transfer/repayment candidates while both account entries remain traceable and reporting avoids double counting.

## Acceptance criteria

- [x] Candidate generation uses normalized evidence; equal/opposite amounts and nearby dates alone cannot prove ownership or pairing.
- [x] Card purchase plus current-account repayment produces spending once and gross current-account outgoing once, with no repayment income.
- [x] Other confirmed tracked-account transfers produce neither spending nor income; keep separate entries and both dates.
- [x] Missing/ambiguous counterparts and excluded-account movements stay reviewable/provisional; never fabricate savings principal transactions.

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

Candidates: `reporting/transfers.py` normalises amounts across account kinds —
equal magnitude with a card on one side and both entries negative suggests a
repayment; opposite signs between current/savings suggest an own transfer.
Candidates are limited to a seven-day display window, exclude the same account
and any already-linked row, and are labelled as signals only; nothing is linked
or reclassified automatically. Multiple candidates stay visible so the user must
choose.

Confirmation: review shows candidates with account, date, amount, days apart and
the suggested kind; confirming requires an explicit POST. Both transaction rows
are locked in ascending primary-key order, membership is rechecked under the
lock, and the stored link is canonical. A barrier test starts overlapping
confirmations (A↔B and B↔C) and asserts exactly one 302, one 400 and one link
containing the shared entry, so one row cannot acquire conflicting semantics.

Reporting: a confirmed link takes precedence (after duplicate suppression and
user corrections). A repayment keeps the paying current-account outgoing once and
gives the card credit no spending/income; an own transfer has no spending,
income or external outgoing. Both entries, dates and source links remain
untraceable — no merge or deletion.

Fixture examples are literal and independent: £80 card purchase + £80 current
repayment + £80 card credit → spending £80 (not £160), cash outgoing £80, income
£0; £50 current→savings transfer → spending/income/outgoing £0 with both rows
retained. Unconfirmed candidates leave machine effects unchanged, and
equal-opposite/nearby-date pairs outside the window are not offered.

Green: `.venv/bin/python manage.py test --noinput` → 192 tests OK;
`./scripts/smoke.sh` → exit 0, 192 tests, `restart check ok`. (One earlier test
run failed because two test suites raced on the same test database; rerun alone
passed.)

Limits: no automatic pairing; the seven-day window is display-only and not an
approved matching rule; missing counterparts stay reviewable; excluded-account
movements remain as they were. No deployment or push. Record red/green commands, behavioral demo, review findings/fixes,
local versus actual-host results, unresolved limits and commit reference when
available. Passing local tests alone cannot close a required real-host gate.
