# Beng Statement Intelligence

Canonical domain language for statement import, transaction review, and financial
reporting. Detailed reporting rules are in HLD section 7.

## Language

**Named account**:
An actual bank or credit-card account identified by a user-chosen name. It is
distinct from a user identity or an uploaded statement.

**Original**:
The unchanged source file received through intake.

**Upload**:
A submitted original and its receipt context, selected account, and processing
history. Multiple uploads may describe overlapping account activity.

**Source entry**:
A transaction or balance observation as represented in a particular original.

**Transaction**:
An account-specific logical record, possibly supported by multiple overlapping
source entries.

**Duplicate match**:
Evidence that source entries represent the same transaction on the same account.
_Avoid_: Transfer link.

**Transfer link**:
A relationship between distinct transactions on different tracked accounts that
represent one money movement.
_Avoid_: Duplicate match.

**Balance observation**:
A source-supported account balance with its date and meaning, used to anchor
historical balances.

**Provenance**:
Evidence connecting facts, interpretations, corrections, and processing results
to their sources.

**User correction**:
A retained user-confirmed replacement or classification with precedence over
subsequent machine output.

**Authoritative state**:
The accepted records, source evidence, and user-confirmed changes used for current
application behavior. A recovery backup is a copy, not a competing authority.

**Reporting period**:
The interval selected for dashboard figures. It is not a data-deletion or
retention boundary.

**Spending**:
Purchase costs, fees, charged interest and cash withdrawals, reduced by refunds
and evidenced reversals; also includes
conversion out of Revolut GBP into foreign currency under the chosen GBP-only
reporting convention, reduced by conversions back into GBP in their posting
period. Excludes card repayments and other tracked own-account transfers.

**Income**:
Identified income such as salary and received interest; excludes own transfers
and refunds.

**Cash outgoing**:
Cash leaving current/debit accounts for external payments, including card
repayments; excludes transfers between tracked own accounts other than those
explicitly included card repayments.

**Net cash position**:
Tracked current/debit and savings balances minus outstanding card debt,
separately by currency.

**Provisional total**:
An aggregate affected by unresolved facts, classification, or matching whose
uncertainty is visible.

**Coverage gap**:
Missing source history or balance evidence that prevents claiming complete
reporting.
