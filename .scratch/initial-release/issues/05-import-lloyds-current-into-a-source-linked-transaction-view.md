# 05: Import Lloyds Current into a source-linked transaction view

Status: done
Claimed by: —
Approval: ticket breakdown approved by Sourav
Blocked by: 04
Parent: [First-release specification](../spec.md)
Acceptance trace: AC-05, AC-17
Worker routing: Budget worker candidate; stronger review required before completion.

## What to build

A Lloyds Current upload is processed by the worker and appears as exact, dated transactions and balance observations with original evidence.

## Acceptance criteria

- [x] Build a synthetic layout fixture and independent expected rows before implementing extraction; handle interleaved accessibility text and continuation headers.
- [x] Normalize money-in/out to exact pence, preserve source descriptions/types/date meanings and locators, and reconcile running/summary balances.
- [x] A failed reconciliation retains the original and prior financial view with a review issue; no guessed rows.
- [x] Demonstrate upload, Process now, assigned-source processing, committed transaction list and source reopening end to end on the Mac.
- [x] Carried from ticket 03: detect a first-time statement whose source identity contradicts the selected named account, show it, and never silently reassign it.

## Test interface and verification

Statement interpretation/reporting, application worker/result interfaces and browser transaction view. Use independently reviewed expected values and the approved
interfaces. For new behavioral code, observe a failing test and implement the minimum slice,
then repeat. Evaluation/evidence work runs the relevant existing checks; do not
create contrived tests of documentation. Include usable integration and meaningful
tests with the behavior rather than leaving a parser or UI stub. Follow [shared execution rules](../ticket-plan.md#execution-proposal)
for review, host evidence and permission limits.

## Prerequisites and scope limit

P-03 Lloyds Current fixture/oracle (including an identity-mismatch fixture); public interpretation interface established by this slice.

One supplied statement layout only. Strong review of initial parser/publication contract is mandatory.

## Completion evidence

Layout evidence: the supplied Lloyds Current statement was re-read locally
(read-only, values masked) and its text structure recorded as the contract:
`CURRENT.`, period line, `Money In.`/`Money Out.`/`Balance on <date>.` anchors,
then vertical transaction blocks (`Date`, `Description`, `Type`,
`Money In (£)`, `Money Out (£)`, `Balance (£)`) separated by interleaved
`Column` accessibility labels and trailing full stops. The fixture mirrors that
structure with invented amounts and descriptions; no private values, account
numbers or text entered the repository.

Fixture/oracle: `ledger/tests/statement_fixtures.py` renders a two-page synthetic
statement; expected rows and balances are hand-computed (opening 1,200.00 + rows
= closing 2,646.80; money in 2,512.44; money out 1,065.64) and recorded as
literals, not derived from the parser.

Interpretation: `interpretation/lloyds_current.py` parses blocks, treats the
unused money column as `blank`, derives direction from the money column, and
validates it against the running-balance delta plus the opening/closing equation
and stated totals. Anything unreadable or contradictory produces an issue and
no financial facts — never a guessed row.

Publication: `jobs/publication.py` re-validates every worker fact at the trust
boundary (integer pence, ISO dates, locators, duplicate source rows,
reconciliation), commits a section atomically, and sets the upload to Imported
or Needs review. A kind mismatch between the statement family and the selected
named account is reported and imports nothing.

Red: missing `interpretation` package and no publication path (11 parser tests,
8 publication tests failing).

Green: `.venv/bin/python manage.py test` → 60 tests OK against real PostgreSQL,
including PDF text extraction reaching identical rows and a live-server worker
subprocess import. `./scripts/smoke.sh` → exit 0, 60 tests, `restart check ok`.

Live Mac demo: uploaded the synthetic statement to Lloyds Current, clicked
Process now, ran `python -m worker` against `runserver` → `{"outcome":
"imported"}`; receipt shows Imported, Job Completed, attempts `downloaded` and
`interpreted`; the account page lists the six dated rows with signed amounts and
running balances and links each to its source page; balance anchors show opening
and closing.

Carried ticket-03 requirement: identity mismatch is now detected when a
first-time Lloyds Current statement is assigned to a non-current account; the
receipt stays on the selected account, requests review and imports nothing.
Same-kind accounts remain indistinguishable — recorded limit.

Limits: one supplied layout only; no prior published view exists to retain on a
failed reprocessing (arrives with reprocessing in later tickets); real-source
extraction against the private PDFs remains a release gate (tickets 29–30); no
overlap/duplicate handling (ticket 15). No deployment or push. Record red/green commands, behavioral demo, review findings/fixes,
local versus actual-host results, unresolved limits and commit reference when
available. Passing local tests alone cannot close a required real-host gate.
