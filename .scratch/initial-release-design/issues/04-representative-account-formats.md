# Representative account formats and expected facts

Type: task
Label: wayfinder:task
Status: resolved
Blocked by: None
Parent: [Initial release technical design](../map.md)

## Question

Obtain representative formats from Sourav for Lloyds Current Account, Lloyds
Credit, Amex Credit, and Revolut Debit before implementation. Establish safely
sanitized fixtures and independently checked expected transactions/balances.
Include available overlap, card repayment, transfer, refund, and currency
examples without asking for every possible format or unnecessary private data.

## Resolution evidence

Document the supported format inventory, date/sign/identifier/balance fields,
and unresolved cases. Raw statements stay outside Git. If full sanitized
fixtures are not yet possible, record why dependent parsing decisions remain
open; planning on independent tickets may continue.

## Answer

Sourav supplied all four PDFs in `/Users/beng/Work/private/bank-statements` for
read-only design and local verification. All open and contain usable text.
See [format inventory and verification](../research/statement-format-inventory.md)
for page/column/period structures, independent reconciliation checks and gaps.
Private originals were not copied into the repository or changed.

The sample acquisition/inspection task is complete; sample-informed import
contracts are now unblocked. Full sanitized fixtures, reviewed expected results,
and complete August coverage remain explicit downstream work, not claimed done.
Revolut includes multiple currencies, joint/savings/crypto sections; their scope
requires a user decision before treating the entire file as supported intake.
