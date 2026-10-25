# 07: Advisory failure and separate bounded recovery

Status: done locally
Claimed by: —
Approval: task division approved by Sourav; planning/publication only.
Execution authorization: authorized by Sourav's instruction to implement the active backlog.
Blocked by: [06](./06-one-validated-suggestion-through-explicit-user-confirmation.md)
Draft reference: T07
Parent: [Authoritative completion specification](../spec.md)
Historical evidence: [27](../../initial-release/issues/27-show-validated-optional-advice-without-risking-financial-imports.md)

## What to deliver

Advisory failure and separate bounded recovery. Complete the end-to-end behavior below, reusing verified existing work rather than rebuilding it.

## Acceptance criteria

- [x] Timeout, missing runtime, malformed output or unsupported source evidence
  leaves deterministic imports and manual review usable.
- [x] Advice retry is bounded and independent of financial reimport; obsolete
  suggestions cannot replace confirmed corrections.
- [x] Show failure, retry and abstention honestly without private content in logs.

## Decision and external gates

D2: bounded timeout/retry and stale-advice contract.
Read the [decision register](../spec.md#decision-register). A resolved decision does not authorize coding or live changes.

## Verification

Controlled adapter failures and real unavailable-runtime smoke; observe independent bounded advice recovery without reimport.

Follow [common completion rules](../spec.md#completion-rules): TDD for changed public behavior, runtime/browser proof, standards and spec review, and separate local/host evidence.

## Current evidence and completion

Completed locally against an intentionally unavailable runtime and then a
controlled local endpoint, proving independent recovery without re-import.

Evidence:
- New explicit advice request path (`AdviceRequest`): review offers "Request local
  advice" for an unresolved row with no open suggestion. The worker drains these
  requests separately from financial jobs, claims only one at a time, reclaims a
  stale claim after the lease, and enforces the shared attempt budget.
- Failure is visible on review ("Last attempt: …"); a failure with attempts left
  is re-queued automatically, and an exhausted request stays failed with "Request
  advice again". Manual retry resets only advice state, never transactions.
- Real local smoke: requested advice through the browser, ran the worker against
  a controlled local endpoint, and saw the suggestion attached to the same
  transaction without re-import (one transaction only). A separate run with
  `INFERENCE_URL=http://127.0.0.1:1` imported the statement, logged one bounded
  advice warning, and left the row manually reviewable.
- Unit tests cover timeout/connection failure, HTTP error, malformed JSON,
  invented classification, invalid advice results and missing fields; none
  re-run the financial import. Logs contain no description, amount or source
  text.
- Test-infrastructure note: live-server worker tests intermittently deadlocked
  during PostgreSQL flush; a bounded flush retry after closing stale connections
  now keeps the suite deterministic (six consecutive green runs).

Implementation commits: `0a8b173`, `17cf8da`, `0a4e747`. Real timeout behaviour
against the actual GPU runtime remains part of tasks05/08.
