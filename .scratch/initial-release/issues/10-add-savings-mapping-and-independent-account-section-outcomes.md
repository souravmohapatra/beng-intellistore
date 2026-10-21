# 10: Add savings mapping and independent account-section outcomes

Status: done
Approval: ticket breakdown approved by Sourav
Blocked by: 09
Parent: [First-release specification](../spec.md)
Acceptance trace: AC-02, AC-10, AC-11, AC-17
Worker routing: Stronger implementation/design oversight and independent review recommended.

## What to build

One Revolut upload populates personal GBP and savings GBP, preserving valid sections when another section fails validation.

## Acceptance criteria

- [x] Confirm both section-to-named-account mappings on first import and reuse only with consistent source identity; never require PDF splitting.
- [x] Publish supplied savings balance observations and explicit interest without inventing principal movements or complete daily history.
- [x] Reconciliation failure retains that section's previous view while valid sections publish in one consistent update with visible partial status.
- [x] Ignored joint/non-GBP/crypto sections cause no false coverage error; unexplained savings changes remain reviewable.

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

Mapping: the upload form now carries an optional confirmed savings account for
consolidated statements; the choice is remembered in session like the primary
account and is never inferred or reassigned. A savings section without a
confirmed mapping is deferred with `mapping_required` and the upload is `partial`
rather than failing silently or attaching to the wrong account.

Interpretation: `interpretation/revolut.py` reads the `Clearbank (GBP)` savings
summary and its interest-only transaction page (date, gross interest, net
interest columns), records opening/closing balances dated from the statement
period and each explicit net-interest receipt. It never invents principal
movements or daily completeness.

Independent outcomes: sections publish independently; a valid personal section
is committed while a failed savings section contributes no rows or balances, and
the effective outcome is `partial` with the upload left at Needs review.
Ignored joint/non-GBP/crypto sections still contribute nothing and do not create
coverage errors. An unexplained savings balance change (beyond listed interest)
is published with a visible `unexplained_savings_change` review note instead of
fabricated rows or a silent pass.

Fixture: savings section with opening £250.00, three £0.10 interest receipts and
closing £250.30, invented and reconciled independently; a mutation raises the
closing balance to prove the review-note path.

Green: `.venv/bin/python manage.py test --noinput` → 104 tests OK;
`./scripts/smoke.sh` → exit 0, 104 tests, `restart check ok`.

Live demo: uploaded the consolidated fixture with Revolut Savings confirmed,
released and ran the worker → `outcome: imported`; the savings account shows the
three interest receipts with dated opening/closing balances; the personal rows
remain on the current account; excluded sections are listed as ignored.

Mapping identity (added after review): confirmed mappings are stored in
`SourceMapping` keyed by a hash of the source's personal account identifier,
with the savings identifier hash when a savings account is mapped. Reuse
requires the same primary account, the same selected savings account, and
matching identifiers; a changed primary/savings identifier requests review with
`source_identity_mismatch` and imports nothing. A document without a labelled
identifier authorises no reuse and stores no mapping. Tests cover stored
identities, a different primary account, a different source identifier (new
mapping), missing identifiers, and a changed savings identifier. Session
preselection is scoped to the selected primary account.

Limits: savings evidence is interest-only by source design; real-source accuracy
remains a release gate. No deployment or push. Record red/green commands, behavioral demo, review findings/fixes,
local versus actual-host results, unresolved limits and commit reference when
available. Passing local tests alone cannot close a required real-host gate.
