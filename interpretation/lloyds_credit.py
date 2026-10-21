"""Deterministic interpretation of the supported Lloyds Credit layout.

Supported layout contract (from the supplied statement's observed structure and
synthetic fixtures): cover/table text identifying ``Lloyds Bank``, a credit card
and a statement date; transaction lines of ``card · transaction date · date
entered · description · amount[CR]`` where dates omit the year; foreign-currency
continuation lines are annotations, never extra billed rows; standalone
``NON-STERLING PURCHASE FEE`` rows are real fees; ``BALANCE FROM PREVIOUS
STATEMENT``/``New balance``/``Payments received`` supply debt anchors.

Card amounts are debt movements: a purchase increases debt (positive), a CR
credit reduces it (negative). Reporting uses the date entered; the transaction
date is retained separately. Payment-due text is never treated as a payment.
"""

import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

LAYOUT_BANK = "Lloyds Bank"
LAYOUT_KIND = "Credit Card"
SECTION_NAME = "lloyds_credit"
ACCOUNT_KIND_HINT = "card"

ROW_PATTERN = re.compile(
    r"^(?:(?P<card>\d{1,2})\s+)?"
    r"(?P<transaction>\d{2} [A-Z]+)\s+"
    r"(?P<entered>\d{2} [A-Z]+)\s+"
    r"(?P<description>.+?)\s+"
    r"(?P<amount>[\d,]+\.\d{2})(?P<cr>CR)?$"
)
FX_CONTINUATION = re.compile(r"^[\d,]+\.\d{2}[A-Z]{3} @ [\d.]+$")
STATEMENT_DATE = re.compile(r"^(\d{2} [A-Z][a-z]+ \d{4})$")
PREVIOUS_BALANCE = re.compile(r"^(?:BALANCE FROM PREVIOUS STATEMENT|Previous balance)\s+([\d,]+\.\d{2})$")
NEW_BALANCE = re.compile(r"^New balance\s+([\d,]+\.\d{2})$")
PAYMENTS_RECEIVED = re.compile(r"^Payments received\s+([\d,]+\.\d{2})$")


@dataclass(frozen=True)
class ParsedTransaction:
    posted_on: date
    transaction_date: date
    description: str
    amount_pence: int
    page: int
    row: int
    source_text: str
    transaction_type: str = ""


@dataclass(frozen=True)
class BalanceAnchor:
    kind: str
    amount_pence: int
    observed_on: date | None = None


@dataclass(frozen=True)
class Issue:
    code: str
    message: str


@dataclass
class ParseResult:
    recognised: bool
    section_name: str = SECTION_NAME
    account_kind_hint: str | None = None
    rows: list[ParsedTransaction] | None = None
    balances: list[BalanceAnchor] | None = None
    issues: list[Issue] | None = None
    reconciled: bool = False
    opening_pence: int | None = None
    closing_pence: int | None = None
    credits_pence: int | None = None
    debits_pence: int | None = None

    def __post_init__(self):
        self.rows = [] if self.rows is None else self.rows
        self.balances = [] if self.balances is None else self.balances
        self.issues = [] if self.issues is None else self.issues


def to_pence(text: str) -> int:
    value = Decimal(text.replace(",", "")) * 100
    if value != value.to_integral_value():
        raise InvalidOperation(text)
    return int(value)


def parse(text: str) -> ParseResult:
    pages = text.split("\f")
    if (
        not pages
        or LAYOUT_BANK not in pages[0]
        or LAYOUT_KIND not in "\n".join(pages)
    ):
        return ParseResult(recognised=False)

    result = ParseResult(recognised=True, account_kind_hint=ACCOUNT_KIND_HINT)
    statement_date = _statement_date(pages[0], result.issues)

    for page_number, page_text in enumerate(pages, start=1):
        for line in page_text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if FX_CONTINUATION.match(stripped):
                continue  # annotation beside the billed GBP amount

            row_match = ROW_PATTERN.match(stripped)
            if row_match and _looks_like_transaction(row_match):
                _consume_row(row_match, page_number, statement_date, result)
                continue

            previous = PREVIOUS_BALANCE.match(stripped)
            if previous:
                amount = _maybe_pence(previous.group(1))
                if amount is not None:
                    if result.opening_pence is None:
                        result.opening_pence = amount
                        result.balances.append(BalanceAnchor("opening", amount, None))
                    elif result.opening_pence != amount:
                        result.issues.append(
                            Issue(
                                "contradictory_balance_anchor",
                                "The statement repeats a different previous balance.",
                            )
                        )
                continue

            new_balance = NEW_BALANCE.match(stripped)
            if new_balance:
                amount = _maybe_pence(new_balance.group(1))
                if amount is not None:
                    if result.closing_pence is None:
                        result.closing_pence = amount
                        result.balances.append(
                            BalanceAnchor("closing", amount, statement_date)
                        )
                    elif result.closing_pence != amount:
                        result.issues.append(
                            Issue(
                                "contradictory_balance_anchor",
                                "The statement repeats a different new balance.",
                            )
                        )
                continue

            payments = PAYMENTS_RECEIVED.match(stripped)
            if payments:
                result.credits_pence = _maybe_pence(payments.group(1))

    _validate(result)
    return result


def _looks_like_transaction(row_match) -> bool:
    return row_match is not None and bool(row_match.group("description"))


def _statement_date(first_page: str, issues: list[Issue]) -> date | None:
    for line in first_page.splitlines():
        match = STATEMENT_DATE.match(line.strip())
        if match:
            try:
                return datetime.strptime(match.group(1), "%d %B %Y").date()
            except ValueError:
                issues.append(
                    Issue("invalid_statement_date", "The statement date is not a valid date.")
                )
                return None
    issues.append(Issue("missing_statement_date", "The statement date was not found."))
    return None


def _infer_year(day_text: str, statement_date: date | None, issues: list[Issue]) -> date | None:
    """Infer the omitted year from the statement date, refusing ambiguity."""
    if statement_date is None:
        return None
    try:
        parsed = datetime.strptime(f"{day_text} {statement_date.year}", "%d %B %Y").date()
    except ValueError:
        issues.append(Issue("invalid_transaction_date", f"Unreadable date: {day_text}."))
        return None
    if parsed > statement_date:
        try:
            parsed = parsed.replace(year=statement_date.year - 1)
        except ValueError:
            return None
    return parsed


def _consume_row(row_match, page_number: int, statement_date: date | None, result: ParseResult) -> None:
    amount = _maybe_pence(row_match.group("amount"))
    if amount is None:
        result.issues.append(
            Issue(
                "malformed_transaction_row",
                f"Unreadable amount on page {page_number}: {row_match.group(0)[:100]}",
            )
        )
        return

    transaction_date = _infer_year(row_match.group("transaction"), statement_date, result.issues)
    entered_date = _infer_year(row_match.group("entered"), statement_date, result.issues)
    if transaction_date is None or entered_date is None:
        result.issues.append(
            Issue(
                "ambiguous_transaction_year",
                f"Could not place the row dated {row_match.group('transaction')} in a year.",
            )
        )
        return

    signed = -amount if row_match.group("cr") else amount
    result.rows.append(
        ParsedTransaction(
            posted_on=entered_date,
            transaction_date=transaction_date,
            description=row_match.group("description").strip(),
            amount_pence=signed,
            page=page_number,
            row=sum(1 for row in result.rows if row.page == page_number) + 1,
            source_text=row_match.group(0),
        )
    )


def _maybe_pence(text: str) -> int | None:
    try:
        return to_pence(text)
    except (InvalidOperation, AttributeError):
        return None


def _validate(result: ParseResult) -> None:
    if result.opening_pence is None:
        result.issues.append(Issue("missing_opening_balance", "No previous balance was found."))
    if result.closing_pence is None:
        result.issues.append(Issue("missing_closing_balance", "No new balance was found."))
    if not result.rows:
        result.issues.append(Issue("no_transactions", "No transaction rows were found."))

    for row in result.rows:
        if row.posted_on > row.transaction_date and (row.posted_on - row.transaction_date).days > 31:
            result.issues.append(
                Issue(
                    "implausible_dates",
                    f"{row.description} has a posting date long before its transaction date.",
                )
            )

    credits = -sum(row.amount_pence for row in result.rows if row.amount_pence < 0)
    debits = sum(row.amount_pence for row in result.rows if row.amount_pence > 0)
    result.debits_pence = debits

    if result.credits_pence is not None and result.credits_pence != credits:
        result.issues.append(
            Issue(
                "totals_mismatch",
                f"Stated payments received {result.credits_pence} pence differ from rows "
                f"{credits} pence.",
            )
        )

    if result.opening_pence is not None and result.closing_pence is not None:
        expected = result.opening_pence + debits - credits
        if expected != result.closing_pence:
            result.issues.append(
                Issue(
                    "closing_balance_mismatch",
                    f"Previous balance plus debits minus credits gives {expected} pence, "
                    f"not the stated {result.closing_pence} pence.",
                )
            )

    result.reconciled = not result.issues
