# 09: Import Revolut personal GBP while ignoring excluded sections

Status: done
Approval: ticket breakdown approved by Sourav
Blocked by: 05
Parent: [First-release specification](../spec.md)
Acceptance trace: AC-02, AC-05, AC-10
Worker routing: Budget worker candidate; stronger review required before completion.

## What to build

A consolidated Revolut original imports personal GBP rows and balances while clearly ignoring joint, non-GBP and crypto sections.

## Acceptance criteria

- [x] Synthetic consolidated fixture includes supported and excluded sections, wrapped rows and repeated summaries; only personal GBP is imported in this slice.
- [x] Retain signed native GBP values, account identity and running balance evidence; GBP equivalents from excluded currencies never create GBP transactions.
- [x] Source original remains unchanged and accessible, with included/excluded sections understandable in processing status.
- [x] Unclear GBP movements to excluded accounts remain reviewable rather than silently confirmed spending or income.

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

Layout evidence: the supplied consolidated export was re-read locally (read-only,
amounts/IBANs masked) and its positions recorded: one text fragment per cell,
date at x≈40, description x≈125, category x≈257, signed ``£`` amount x≈342,
running balance x≈385, tax/other/fees to the right; wrapped descriptions sit one
line below; each section repeats ``Custom Statement`` and the period
``Aug 1, 2026 - Aug 31, 2026``; personal GBP, personal USD/SEK, joint GBP,
savings and crypto each have their own summary and transaction pages.

Fixture: `revolut_pages` builds per-cell positioned tokens (now one PDF text
object per cell, matching the producer) with invented values: opening £500.00,
rows −£12.40, −£30.00, +£25.00, −£7.60 and closing £475.00; excluded USD, joint,
savings and crypto sections are present.

Interpretation: `interpretation/revolut.py` imports only the personal GBP
section, keeps signed native GBP values, retains running balances and category,
appends wrapped description fragments, dates anchors from the statement period,
and rejects `$`/`SEK` amounts rather than treating them as GBP. It reports
`personal_account_usd`, `joint_account_gbp` and `crypto` as ignored, and
`savings_account_gbp` as deferred (savings belongs to ticket 10).

Publication: ignored sections contribute nothing; a deferred section keeps the
upload at Needs review and the effective outcome is reported as `partial` (new
server-derived outcome), so a statement containing savings never claims a
complete import. GBP rows from excluded sections never appear.

Green: `.venv/bin/python manage.py test` → 100 tests OK; `./scripts/smoke.sh` →
exit 0, 100 tests, `restart check ok`.

Live demo: uploaded the synthetic consolidated PDF to a current account,
released it and ran the worker → `outcome: partial`; the receipt lists
`personal_account_usd — ignored`, `joint_account_gbp — ignored`, `crypto —
ignored` and `savings_account_gbp — deferred`; the account page shows the four
personal GBP rows with balances, and none of the excluded rows.

Observed gap (ticket 18 scope): a worker crash after claiming left the job in
Processing with no expiry, so the next run could not claim; the dev database was
repaired manually. Expired-claim recovery is not implemented here.

Limits: savings and its interest evidence are deferred (ticket 10); no
GBP-equivalent conversion from excluded currencies; real-source accuracy remains
a release gate. No deployment or push. Record red/green commands, behavioral demo, review findings/fixes,
local versus actual-host results, unresolved limits and commit reference when
available. Passing local tests alone cannot close a required real-host gate.
