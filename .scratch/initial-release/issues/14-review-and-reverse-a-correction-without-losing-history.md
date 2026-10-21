# 14: Review and reverse a correction without losing history

Status: done
Approval: ticket breakdown approved by Sourav
Blocked by: 11
Parent: [First-release specification](../spec.md)
Acceptance trace: AC-13
Worker routing: Stronger implementation/design oversight and independent review recommended.

## What to build

A user resolves one issue beside source evidence and sees the effect of an explicit correction, with a validated history-preserving revert.

## Acceptance criteria

- [x] Show source page/row, extracted value, proposed edit/match and before/after effect; require explicit save/confirm/reject.
- [x] Keep extracted values separate from confirmed overrides and update affected committed reporting consistently.
- [x] Reverting restores the source-derived value through validation and retains correction history; no silent deletion of evidence.
- [x] Create a concurrent-edit/reprocessing acceptance case for later adversarial publication verification; unconfirmed suggestions have no effects.

## Test interface and verification

Application review/report interfaces and browser review journey. Use independently reviewed expected values and the approved
interfaces. For new behavioral code, observe a failing test and implement the minimum slice,
then repeat. Evaluation/evidence work runs the relevant existing checks; do not
create contrived tests of documentation. Include usable integration and meaningful
tests with the behavior rather than leaving a parser or UI stub. Follow [shared execution rules](../ticket-plan.md#execution-proposal)
for review, host evidence and permission limits.

## Prerequisites and scope limit

P-02 correction ownership/history contract; independent correction/revert examples.

No bulk approval or rule-learning engine.

## Completion evidence

Model: `Correction` is append-only history (classification, note, created,
reverted) linked to the transaction; extracted values are never modified.
Creating a confirmation marks any prior active correction reverted, so exactly
one override is active and every step remains in history.

Review journey: `/review/` lists unresolved or corrected transactions with
source links; `/review/<transaction>/` shows the original filename/page/row,
source text, extracted description/type/amount/date, the machine classification
and the effect of each classification option. Nothing changes on GET; POST
requires choosing a classification and pressing Save correction. Revert marks
the active correction reverted and the machine-derived value resumes.

Direction validation (added after review): a confirmation must agree with the
source's signed direction — an outflow cannot be confirmed as income or a refund,
a card credit cannot be income (but can be a refund), transfers are allowed in
either direction. Invalid attempts return 400 with a visible message and save
nothing; inapplicable options are disabled in the form.

Reporting: `classify` now gives confirmed corrections precedence over machine
classification, using sign-preserving effects; totals, drill-down and dashboard
follow automatically.

Green: `.venv/bin/python manage.py test --noinput` → 170 tests OK;
`./scripts/smoke.sh` → exit 0, 170 tests, `restart check ok`.

Live demo: corrected a transfer to an excluded product as “Transfer between own
accounts” with a note — the active correction appeared and the receipt kept its
source evidence; reverting restored “Unresolved: excluded from totals
(provisional)” and the history showed the reverted entry with its timestamp.

Carried forward: a concurrent-edit/reprocessing case (correction surviving a
later publication, conflicting machine output flagged) is ticket 19's
adversarial verification; here no reprocessing path can overwrite a correction.

Limits: one classification override per transaction at a time (history keeps the
rest); no bulk approval or rule learning. No deployment or push. Record red/green commands, behavioral demo, review findings/fixes,
local versus actual-host results, unresolved limits and commit reference when
available. Passing local tests alone cannot close a required real-host gate.
