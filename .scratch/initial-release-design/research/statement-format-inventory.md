# Supplied statement format inventory

Read-only inspection on 2026-10-18. Originals remain in the user-supplied private
statement directory outside the repository. No copies, rendered pages, raw text,
account identifiers, merchant lists or financial amounts belong in this note.
This documents observed formats, not a production parser or approved expansion
of product scope. All four PDFs have usable text and open without a password.

## Observed layouts

| Source | Pages | Relevant structure and boundaries |
| --- | --- | --- |
| Lloyds Current | 2 | Calendar-month August 2026 export. Date, description, transaction type, separate money-in/out columns and running balance; opening/closing balances and period totals. Transaction table continues to page 2. |
| Lloyds Credit | 5 | Statement dated 5 August 2026; observed transactions span July into early August. Transaction date and date entered are distinct. Card suffix, description, GBP amount and CR marker; foreign-currency/rate continuation lines and separate non-sterling fee rows. Previous/new balance and payment/debit summaries. |
| Amex Credit | 7 | Period explicitly 11 August–10 September 2026. Transaction and process dates; GBP billed amount, credit marker sometimes on a following line, multiline merchant and FX details. Monthly table on page 3; appended annual summary on page 7 must not become new transactions or a monthly balance. |
| Revolut consolidated | 20 | Calendar-month August 2026 custom export. Personal current accounts in GBP/USD/SEK, joint GBP account, savings and crypto sections. Summary and transaction sections repeat by account/currency. Transaction amounts are signed; running balances and wrapped descriptions. Native currency and displayed GBP equivalents coexist. |

Lloyds Current extraction contains tiny accessibility labels interleaved with
visible text; generic `extract_tables()` did not recover its transaction rows.
A diagnostic visible-text filter and positioned words recovered the observed
rows, verified against the rendered page and balances. Production rules must
recognize this exact format and validate results rather than assume generic
table extraction works. The exploratory font-size filter is not yet a supported
parser contract.

Amex's FX fee is disclosed alongside a billed GBP transaction amount. The sum
of billed rows already reconciles to new debits; adding the disclosed fee again
would double count it. Lloyds Credit, by contrast, has standalone fee rows.
Neither statement's payment due amount/date is evidence of an executed payment.
Use process/date-entered for reporting under the agreed posting-date rule, keeping
transaction date separately. Infer omitted years only from defensible statement
context; year-boundary behavior still needs a fixture.

Revolut is not one debit-account table. Joint ownership, savings, crypto and
cross-currency conversion require explicit scope/matching decisions. Do not
silently combine balances or treat every incoming transfer as income. Savings
transaction pages explicitly describe interest receipts only: they cannot prove
complete savings movement history. FX-equivalent amounts are annotations, not
additional GBP transactions. No FX consolidation rule is approved.

## Verification performed

These were disposable independent inspection checks with Decimal arithmetic,
not application tests or reusable parser code:

- Lloyds Current: 17 source transaction rows; every running-balance transition,
  money-in/out totals and opening/closing equation reconciled.
- Lloyds Credit: 78 rows (77 debits, one payment credit); debit and credit sums
  matched their statement summaries. Opening debt minus credits plus debits
  reconciles with closing debt. CR may directly follow the amount without space.
- Amex: 12 billed debit rows and one payment credit; billed debits matched the
  monthly new-debit summary and the opening/credit/debit/closing equation.
  Following-line CR and FX continuations visually checked.
- Revolut: personal GBP 10 rows and joint GBP 3 rows; all running balances and
  closing balances reconciled against their respective opening summaries.
  USD/SEK, savings and crypto structures were inspected; their full arithmetic
  and financial treatment are not verified by these GBP checks.
- Visually inspected transaction pages for all four layouts, including both
  Revolut personal/joint GBP tables. This was not a full visual audit of all pages.

An initial exploratory credit-row check missed a CR without whitespace, and a
Revolut date selector included a period heading. Narrowing those selectors made
the checks pass. These are fixture cases to retain, not parser defects fixed in
an application. No production parser exists yet.

## Verification gaps and next decisions

The four formats are received and sufficient to proceed with sample-informed
design. They do not establish complete August coverage across all accounts:
card cycles differ, and adjacent statements may be needed for an August oracle.
Only one export per source is present, so overlapping-import identity and repeat
transactions across adjacent statements are not demonstrated. The observed
Amex repayment can inform matching across posting dates; no complete set of
Lloyds August repayment counterparts is established.

Before implementation, specify supported Revolut sections/account mapping,
foreign-currency conversion handling without consolidated FX reporting, fee
waivers/returned payments, transfers to untracked savings/investment/crypto
accounts, date/CR extraction rules, and review behavior for incomplete evidence.
Do not automatically classify these movements from provider labels alone.

Create synthetic layout fixtures and independently reviewed expected results
through the import/test-contract decisions. Reuse private originals for optional
local acceptance checks through an explicit external path; never copy them into
Git or use the same production parser to manufacture its expected results.
Exact private expected amounts can be reread from the originals for those checks;
this inventory deliberately retains only non-sensitive counts and conclusions.
