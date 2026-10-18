# Import contract and worked examples

Design examples only, 2026-10-18. All amounts below are invented. No production
parser or reusable fixtures exist yet. These examples apply accepted HLD rules;
private format evidence is in [the inventory](statement-format-inventory.md).

## Deterministic normalization and provenance

- Normalize GBP ledger movements to integer pence; retain the original amount,
  sign/CR marker and currency evidence. Do not use binary floating point or
  silently round malformed source amounts. Original FX values remain source
  annotations, not extra GBP movements.
- Account cash movement is positive for incoming and negative for outgoing.
  For cards, purchases increase debt and payments/credits reduce debt. A card
  purchase is not a debit-account cash outgoing until its repayment occurs.
- Lloyds Current uses money-in/out columns and running balances. Lloyds Credit
  uses date entered for reporting and CR to distinguish credits; retain purchase
  date. Amex uses process date and handles a following-line CR. Revolut uses its
  supported account section, native GBP signed amount and supplied date.
- Do not infer reporting dates from filenames. Omitted years require defensible
  statement context, including year boundaries; ambiguity requires review.
- A source locator identifies original, account section, page and row/text region.
  Keep evidence for every normalized fact. The exact storage schema is later work.

## Intake and publication boundaries

Reject unreadable/corrupt, password-protected and image-only inputs; reject above
20 MiB per file or 100 PDF pages. Report why. No OCR/password workflow. Check
content rather than trusting file extensions. Readable accepted files with
unsupported layouts stay preserved with an unsupported/review status, not a
successful transaction import. Text/CSV support remains limited to explicitly
specified layouts; the four supplied PDFs do not demonstrate those layouts.

One upload remains one job and one consistent publication transaction. It may
contain separately validated personal GBP and savings GBP sections. A failed
section contributes no new financial facts: retain its prior published view and
its original/evidence. Independently valid sections may be committed together
with a visible partial outcome and per-section problems. An attempt is not
reported as completely imported when any supported section failed.

Check running balances, period totals and opening/closing equations where the
source supplies them. Ignore unsupported Revolut sections intentionally. An
interest-only savings section cannot be required to prove unlisted principal
movements: retain supplied balance observations and explicit interest, flag
unexplained changes and incomplete daily history. Do not fill discrepancies with
invented transactions. Corrections and stale-attempt protections still apply.

## Matching boundaries

Identical original bytes on the same confirmed account/section mapping must not
add financial effects on repeated upload or retry. Preserve a receipt/provenance
relationship without silently changing account association.

For different originals, date/amount/description equality is only a candidate,
not proof that two rows are the same transaction. Source-supported stable
identity or unambiguous overlapping sequence/balance evidence can establish a
match; ambiguous cases require review and retain both source entries. The
fixtures/spec must demonstrate any automated evidence rule before enabling it.
Repeated identical purchases within one statement must not collapse.

Transfer linking relates distinct transactions on different tracked accounts.
Equal/opposite amounts and nearby dates identify candidates, but cannot alone
prove account ownership or a pairing. Use supported counterparty/account evidence;
multiple candidates, missing counterpart or uncertain ownership remain reviewable.
Keep both dates and entries. No heuristic date window is a new approved automatic
match threshold. Unknown classifications make affected totals provisional.

## Independently calculated examples

| Trigger | Expected result |
| --- | --- |
| Same original submitted twice for the same accounts | One set of financial effects; both receipts can point to the preserved evidence. |
| Two separate £12.00 purchases with the same date/description | Preserve both unless stronger duplicate evidence establishes otherwise; the tuple alone cannot merge them. |
| £80 card purchase, then £80 current-account repayment paired with card credit | Spending £80 at purchase posting; cash outgoing £80 at repayment posting; no new income or extra spending from the pair. |
| £50 transfer from tracked current account to tracked savings | Neither spending nor income; no external cash outgoing; combined net cash unchanged once both legs/balances are evidenced. Missing savings detail is not permission to fabricate it. |
| £100 Revolut GBP converted out; £25 converted back in a later period | First period spending/cash outgoing £100. Later period spending -£25, incoming cash £25, income £0. Do not import foreign legs or later foreign purchases. |
| £40 cash withdrawal | Spending £40 and cash outgoing £40; no cash-wallet ledger. |
| £5 fee followed by an evidenced £5 waiver | Net fee spending £0. Waiver is not income. Raw debit-account outgoing remains £5 under the gross outgoing metric. |
| Returned payment whose original classification is known | Reverse that classification; do not invent income. If the counterpart is uncertain, request review. |
| £20 debit from personal GBP to an excluded product | Personal balance falls £20; retain the GBP-side movement. Unclear spending classification is reviewable/provisional; do not import the excluded product. |
| Valid personal GBP section plus unreconciled savings section | Publish validated personal facts with partial status; preserve previous savings view and explain the unresolved section. |
| User correction arrives while reprocessing | Correction takes precedence; contradictory machine output is flagged. Unsafe identity mapping retains the prior view. |

These examples are acceptance inputs for later TDD. The same future production
parser must not generate its own expected values. Additional adjacent statement
coverage, year boundaries and overlap examples are still needed to verify rules
against private originals; they do not authorize broadening supported layouts.
