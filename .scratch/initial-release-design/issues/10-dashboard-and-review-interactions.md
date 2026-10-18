# Dashboard evidence and review interactions

Type: grilling
Label: wayfinder:grilling
Status: resolved
Blocked by: 07
Parent: [Initial release technical design](../map.md)

## Question

Settle period defaults, currency-separated metrics/history, coverage and
provisional indications, source drill-down, uploads and simple text search,
and correction/match-confirmation interactions. Establish the smallest usable
desktop/phone experience without adding advanced search or new financial scope.

## Resolution evidence

Agreed user flows, visible states, and acceptance examples. If text cannot settle
a specific interaction, create a bounded prototype decision rather than
starting the application implementation.

## Confirmed interactions

Sourav accepted Q63-Q66:

- Retain the agreed last-twelve-month default; offer month/year/custom ranges.
  One period controls spending/income/outgoing totals and net-cash history.
  Clicking a metric opens its contributing transaction list with inclusions,
  exclusions and provisional items explainable; simple description search remains.
- Show current/debit/savings balances and card debt by named account, with dated
  evidence and incomplete/provisional badges. Net cash graph does not connect
  unsupported gaps as verified daily history; sparse savings evidence may appear
  as dated points. Review/coverage indicators link to the relevant problem.
- Review one issue at a time with original page/row evidence, extracted values,
  proposed correction/match and before/after effect. Explicit save/confirm/reject;
  allow removing a correction to restore the source-derived value, retain history
  and revalidate, no bulk approval initially.
- Support the same core dashboard/upload/search/review flows on phone and desktop;
  stacked forms/cards on phone rather than requiring a wide table. A dedicated
  application or advanced visual design choices are outside this decision.

## Answer

Dashboard/review interaction decision complete following Sourav's acceptance.
The four confirmed choices above retain the agreed reporting scope, provide
metric-to-source explanation and honest balance coverage, protect explicit
corrections, and support the same core flows on phone and desktop.

Observable acceptance examples for the later spec/tests:

- Selecting August changes all period metrics and graph bounds together. Opening
  spending retains that period and shows contributing transactions plus explicit
  exclusions/provisional issues; simple description search preserves context.
- A savings balance known only at statement boundaries appears as dated evidence,
  not an invented continuous daily balance. Missing account evidence prevents
  presenting an unqualified complete combined total.
- A review issue opens its original source evidence, extracted value and proposed
  change/match. Saving applies a retained user correction and updates affected
  committed figures; rejecting a match keeps distinct transactions. Reverting a
  correction restores the source-derived value through validation and history,
  not deletion of the original or silent removal of audit evidence.
- A phone user can upload, inspect processing/partial failures, find a transaction
  and complete review without requiring a desktop-width table. Process now and
  last-success/failure visibility retain their agreed behavior on both layouts.

Source access remains authenticated; no external document viewer or new service
is selected. Aesthetic design, exact components/layout and accessible browser
implementation are later work. No prototype was necessary for these policy
choices; no UI, accessibility or actual-device acceptance tests have run.
