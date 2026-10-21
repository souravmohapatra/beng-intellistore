"""Deterministic interpretation of the supported Amex statement layout.

Amex text extracts as positioned fragments, so this parser consumes
``(x, y, text)`` tokens per page, reconstructs a line per vertical position and
then reads the monthly table: ``transaction month/day · process month/day ·
details · amount`` with a ``CR`` marker on the following line for credits.
Foreign-spend and exchange-rate fragments are annotations. Annual-summary pages
carry no date columns and are ignored. Card amounts are debt movements, and the
process date is the reporting date while the transaction date is retained.
"""

import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

MONTHS = "JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC"
ROW_PATTERN = re.compile(
    rf"^(?P<txn_month>{MONTHS})\s*(?P<txn_day>\d{{1,2}})\s+"
    rf"(?P<process_month>{MONTHS})\s*(?P<process_day>\d{{1,2}})\s+"
    rf"(?P<description>.+?)\s+£?\s*(?P<amount>[\d,]+\.\d{{2}})$",
    re.IGNORECASE,
)
STATEMENT_DATE_PATTERN = re.compile(r"\b(\d{2})\s*/\s*(\d{2})\s*/\s*(\d{2})\b")
PREVIOUS_BALANCE = re.compile(r"^Previous Balance\b.*?([\d,]+\.\d{2})$")
NEW_BALANCE = re.compile(r"^New Balance\b.*?([\d,]+\.\d{2})$")
PAYMENTS_AND_CREDITS = re.compile(r"^Payments and Credits\b.*?([\d,]+\.\d{2})$")
SECTION_NAME = "amex"
ACCOUNT_KIND_HINT = "card"


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
    payments_and_credits_pence: int | None = None
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


def parse(tokens: list[tuple[float, float, str]]) -> ParseResult:
    return parse_pages([tokens])


def parse_pages(pages: list[list[tuple[float, float, str]]]) -> ParseResult:
    lines_per_page = [_reconstruct_lines(page) for page in pages]
    flat = [line for page in lines_per_page for line in page]
    if not any("Statement of Account" in line or "Transaction Details" in line for line in flat):
        return ParseResult(recognised=False)

    result = ParseResult(recognised=True, account_kind_hint=ACCOUNT_KIND_HINT)
    statement_date = _statement_date(lines_per_page)
    if statement_date is None:
        result.issues.append(
            Issue("missing_statement_date", "The statement date was not found.")
        )

    for page_number, lines in enumerate(lines_per_page, start=1):
        index = 0
        while index < len(lines):
            line = lines[index]
            index += 1

            previous = PREVIOUS_BALANCE.match(line)
            if previous:
                amount = _maybe_pence(previous.group(1))
                if amount is not None and result.opening_pence is None:
                    result.opening_pence = amount
                    result.balances.append(BalanceAnchor("opening", amount, None))
                continue

            new_balance = NEW_BALANCE.match(line)
            if new_balance:
                amount = _maybe_pence(new_balance.group(1))
                if amount is not None and result.closing_pence is None:
                    result.closing_pence = amount
                    result.balances.append(
                        BalanceAnchor("closing", amount, statement_date)
                    )
                continue

            payments = PAYMENTS_AND_CREDITS.match(line)
            if payments:
                amount = _maybe_pence(payments.group(1))
                if amount is not None:
                    if result.payments_and_credits_pence is None:
                        result.payments_and_credits_pence = amount
                    elif result.payments_and_credits_pence != amount:
                        result.issues.append(
                            Issue(
                                "contradictory_payment_summary",
                                "The statement repeats a different payments-and-credits total.",
                            )
                        )
                continue

            row = ROW_PATTERN.match(line)
            if row is None:
                continue

            credit = index < len(lines) and lines[index].strip().upper() == "CR"
            if credit:
                index += 1
            _consume_row(row, credit, page_number, statement_date, result)

    _validate(result)
    return result


BASELINE_TOLERANCE = 3.0


def _reconstruct_lines(tokens: list[tuple[float, float, str]]) -> list[str]:
    """Cluster tokens into text lines by baseline, tolerating small jitter."""
    items = sorted(
        ((y, x, text.strip()) for x, y, text in tokens if text.strip()),
        key=lambda item: (-item[0], item[1]),
    )
    clusters: list[tuple[float, list[tuple[float, str]]]] = []
    for y, x, text in items:
        if clusters and abs(clusters[-1][0] - y) <= BASELINE_TOLERANCE:
            clusters[-1][1].append((x, text))
        else:
            clusters.append((y, [(x, text)]))
    return [
        " ".join(text for _x, text in sorted(group, key=lambda item: item[0]))
        for _y, group in clusters
    ]


def _statement_date(lines_per_page) -> date | None:
    for lines in lines_per_page:
        for line in lines:
            match = STATEMENT_DATE_PATTERN.search(line)
            if match:
                day, month, year = match.groups()
                try:
                    return date(2000 + int(year), int(month), int(day))
                except ValueError:
                    return None
    return None


def _infer_year(month_text: str, day_text: str, statement_date: date | None, issues: list[Issue]):
    if statement_date is None:
        return None
    try:
        parsed = datetime.strptime(
            f"{day_text} {month_text.title()} {statement_date.year}", "%d %b %Y"
        ).date()
    except ValueError:
        issues.append(Issue("invalid_transaction_date", "An unreadable transaction date was found."))
        return None
    if parsed > statement_date:
        try:
            parsed = parsed.replace(year=statement_date.year - 1)
        except ValueError:
            return None
    return parsed


def _consume_row(row, credit: bool, page_number: int, statement_date, result: ParseResult) -> None:
    amount = _maybe_pence(row.group("amount"))
    if amount is None:
        result.issues.append(
            Issue("malformed_transaction_row", f"Unreadable amount on page {page_number}.")
        )
        return
    transaction_date = _infer_year(row.group("txn_month"), row.group("txn_day"), statement_date, result.issues)
    process_date = _infer_year(row.group("process_month"), row.group("process_day"), statement_date, result.issues)
    if transaction_date is None or process_date is None:
        result.issues.append(
            Issue(
                "ambiguous_transaction_year",
                f"Could not place {row.group(0)[:80]} in a year.",
            )
        )
        return

    result.rows.append(
        ParsedTransaction(
            posted_on=process_date,
            transaction_date=transaction_date,
            description=row.group("description").strip(),
            amount_pence=-amount if credit else amount,
            page=page_number,
            row=sum(1 for row in result.rows if row.page == page_number) + 1,
            source_text=row.group(0) + (" CR" if credit else ""),
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

    credits = -sum(row.amount_pence for row in result.rows if row.amount_pence < 0)
    debits = sum(row.amount_pence for row in result.rows if row.amount_pence > 0)
    result.debits_pence = debits

    if result.payments_and_credits_pence is None:
        result.issues.append(
            Issue("missing_payments_summary", "The payments-and-credits summary was not found.")
        )
    elif result.payments_and_credits_pence != credits:
        result.issues.append(
            Issue(
                "totals_mismatch",
                f"Stated payments and credits {result.payments_and_credits_pence} pence differ "
                f"from rows {credits} pence.",
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
