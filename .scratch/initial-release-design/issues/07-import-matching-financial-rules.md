# Import, matching, and financial rule contracts

Type: grilling
Label: wayfinder:grilling
Status: resolved
Blocked by: 04
Parent: [Initial release technical design](../map.md)

## Question

Using supplied examples, settle supported intake/rejection behavior, field/date/
sign normalization, balance anchors/coverage, exact overlap matching, card
settlement/own-transfer linking, and review/correction behavior. Resolve cash
withdrawals and any source-specific classification cases; retain separate
source transactions and explicit uncertainty rather than inventing identities.

## Resolution evidence

Worked examples with independently established expected dashboard effects,
matching confidence/review rules and format limits. Distinguish agreed financial
semantics in the HLD from new sample-dependent decisions.

## Confirmed Revolut simplification

Sourav explicitly chooses GBP-only Revolut tracking. Ignore other currency
accounts and crypto sections. A conversion out of Revolut GBP into a foreign
currency counts as spending when the GBP debit posts, and as GBP cash outgoing.
Do not ingest the foreign-currency leg or its later purchases, or require those
excluded accounts to complete GBP reporting. Preserve the original unchanged.
This is a deliberate personal reporting convention, not an FX valuation model.

### Confirmed account scope and conversion returns

Q55: Sourav selects only Revolut personal GBP and savings GBP. Exclude joint
accounts, non-GBP accounts and crypto sections, even when present in the same
original. This supersedes the proposal to include joint GBP and defer savings.

Q56: Sourav answered yes to treating conversion back into GBP as a spending
reduction in the posting period, describing it as an incoming transaction.
Record the incoming cash movement; its accepted reporting classification is
returned spending, not newly earned income. Do not infer that all GBP credits
are income. This interpretation was explicitly stated back to Sourav.

Remaining work: intake/rejection boundaries, cash withdrawals and reversal
classification, and worked matching/validation contracts.

Q57 accepted: include supplied savings balance observations in net cash,
record explicit interest as income, and avoid inventing savings principal
movements or a complete daily history from an interest-only transaction export.
Flag unexplained balance changes and request fuller evidence when necessary.

### Confirmed upload mapping and excluded-account movements

Q58 accepted: one Revolut upload/job may contribute to both supported named accounts,
personal GBP and savings GBP, with section-to-account mapping confirmed on first
import and reused only while source identity remains consistent. Ignore excluded
sections and keep source provenance for each supported section. No manual split
of the original is needed.

Q59 accepted: retain GBP cash movements to/from excluded joint/crypto/investment accounts,
without importing those accounts. Flag unclear spending/income classifications
for review rather than guessing. Balances reflect the posted movements; affected
spending/income totals remain provisional pending classification. Accepted FX
conversion-out and conversion-back rules remain explicit exceptions.

### Confirmed intake, reversal and reconciliation policies

Q60 accepted: reject unreadable, corrupt, password-protected or image-only files with a
clear reason; initial per-file cap 20 MiB and PDF cap 100 pages. A readable
accepted original with an unsupported layout remains preserved and flagged for
review; never claim transactions were imported. No OCR/password workflow.

Q61 accepted: treat cash withdrawals as spending and cash outgoing at withdrawal time,
without a cash-wallet ledger. Explicit fee waivers reverse fee spending;
returned payments reverse the original classification when evidence identifies
the counterpart, otherwise request review rather than count the credit as income.

Q62 accepted: on failed transaction arithmetic or statement reconciliation, preserve the
original and evidence, block financial publication for the affected account
section and retain its last committed view. Valid unrelated account sections
may publish within the same validated upload result, with partial status visible.
Exclude intentionally ignored sections and do not demand full savings principal
history from an interest-only export. Never repair a discrepancy with guessed
transactions or amounts.

## Answer

Sourav accepted the rules through Q62. The HLD incorporates Revolut scope,
conversion spending/returns, savings coverage, upload mapping, excluded-account
movements, intake limits, cash/reversals and section-level reconciliation gates.
Existing conservative duplicate/transfer and correction rules remain in force;
no unverified heuristic threshold is approved by this resolution.

[Contract and invented worked examples](../research/import-contract-examples.md)
record normalization, provenance, safe matching boundaries and expected reporting
effects. [Private-format inspection](../research/statement-format-inventory.md)
provides selected reconciliation evidence without exposing amounts or identities.

Decision complete. Exact parser implementations, evidence rules, schemas, source
locators and synthetic fixtures belong in specifications/tests. Different card
cycles do not establish complete August coverage; adjacent originals, year-boundary
and overlap cases still need verification. No parser or deployment is implemented.
