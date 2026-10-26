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
from dataclasses import dataclass, replace
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
# Account-summary box: previous closing balance - new credits + new debits =
# closing balance, beneath the corresponding four column headings.
ACCOUNT_SUMMARY = re.compile(
    r"^£?\s*(?P<previous>[\d,]+\.\d{2})\s*-\s*£?\s*(?P<credits>[\d,]+\.\d{2})"
    r"\s*\+\s*£?\s*(?P<debits>[\d,]+\.\d{2})\s*=\s*£?\s*(?P<closing>[\d,]+\.\d{2})$"
)
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
    stated_debits_pence: int | None = None

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


@dataclass(frozen=True)
class _Line:
    y: float
    text: str
    min_x: float


def parse_pages(pages: list[list[tuple[float, float, str]]]) -> ParseResult:
    lines_per_page = [_reconstruct_lines(page) for page in pages]
    flat = [line.text for page in lines_per_page for line in page]
    if not any("Statement of Account" in line or "Transaction Details" in line for line in flat):
        return ParseResult(recognised=False)

    result = ParseResult(recognised=True, account_kind_hint=ACCOUNT_KIND_HINT)
    statement_date = _statement_date(lines_per_page)
    if statement_date is None:
        result.issues.append(
            Issue("missing_statement_date", "The statement date was not found.")
        )

    continuations: list[tuple[int, _Line]] = []
    row_positions: list[tuple[int, float]] = []

    for page_number, lines in enumerate(lines_per_page, start=1):
        consumed: set[int] = set()
        index = 0
        while index < len(lines):
            if index in consumed:
                index += 1
                continue
            line = lines[index]
            index += 1

            previous = PREVIOUS_BALANCE.match(line.text)
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

            new_balance = NEW_BALANCE.match(line.text)
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

            payments = PAYMENTS_AND_CREDITS.match(line.text)
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

            summary = ACCOUNT_SUMMARY.match(line.text)
            if summary:
                _consume_summary(summary, statement_date, result)
                continue

            row = ROW_PATTERN.match(line.text)
            if row is None:
                if _is_continuation(line) and result.rows:
                    continuations.append((page_number, line))
                continue

            credit = False
            for lookahead in range(index, min(index + 2, len(lines))):
                if lines[lookahead].text.strip().upper() == "CR":
                    credit = True
                    consumed.add(lookahead)
                    break
            before = len(result.rows)
            _consume_row(row, credit, page_number, statement_date, result)
            if len(result.rows) > before:
                row_positions.append((page_number, line.y, before))

    _attach_continuations(result, continuations, row_positions)
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
        _Line(
            y=y,
            text=" ".join(text for _x, text in sorted(group, key=lambda item: item[0])),
            min_x=min(x for x, _text in group),
        )
        for y, group in clusters
    ]


def _statement_date(lines_per_page) -> date | None:
    """Take the date nearest the cover's ``Date`` field, not any reference date."""
    for lines in lines_per_page[:1]:
        header_ys = [
            line.y
            for line in lines
            if re.search(r"\bDate\b", line.text) and "Transaction" not in line.text
        ]
        candidates = []
        for line in lines:
            match = STATEMENT_DATE_PATTERN.search(line.text)
            if not match:
                continue
            day, month, year = match.groups()
            try:
                parsed = date(2000 + int(year), int(month), int(day))
            except ValueError:
                continue
            candidates.append((line.y, parsed))
        if not candidates:
            continue
        if header_ys:
            header_y = min(header_ys, key=lambda y: min(abs(y - c[0]) for c in candidates))
            nearest = min(candidates, key=lambda c: abs(c[0] - header_y))
            if abs(nearest[0] - header_y) <= 40:
                return nearest[1]
            continue
        if len(candidates) == 1:
            return candidates[0][1]
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
    if statement_date is not None and not (transaction_date <= process_date <= statement_date):
        result.issues.append(
            Issue(
                "implausible_dates",
                f"{row.group('description').strip()} is processed on "
                f"{process_date.isoformat()} but transacted on {transaction_date.isoformat()}.",
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


def _consume_summary(row, statement_date, result: ParseResult) -> None:
    """Read the account-summary box's previous/credits/debits/closing figures.

    The box states ``previous closing balance - new credits + new debits =
    closing balance``; the credits and debits columns are the statement totals
    the rows must independently reproduce.
    """
    previous = _maybe_pence(row.group("previous"))
    if previous is not None:
        if result.opening_pence is None:
            result.opening_pence = previous
            result.balances.append(BalanceAnchor("opening", previous, None))
        elif result.opening_pence != previous:
            result.issues.append(
                Issue(
                    "contradictory_balance_anchor",
                    "The statement repeats a different previous balance.",
                )
            )

    credits = _maybe_pence(row.group("credits"))
    if credits is not None:
        if result.payments_and_credits_pence is None:
            result.payments_and_credits_pence = credits
        elif result.payments_and_credits_pence != credits:
            result.issues.append(
                Issue(
                    "contradictory_payment_summary",
                    "The statement repeats a different payments-and-credits total.",
                )
            )

    closing = _maybe_pence(row.group("closing"))
    if closing is not None:
        if result.closing_pence is None:
            result.closing_pence = closing
            result.balances.append(BalanceAnchor("closing", closing, statement_date))
        elif result.closing_pence != closing:
            result.issues.append(
                Issue(
                    "contradictory_balance_anchor",
                    "The statement repeats a different new balance.",
                )
            )

    debits = _maybe_pence(row.group("debits"))
    if debits is not None:
        if result.stated_debits_pence is None:
            result.stated_debits_pence = debits
        elif result.stated_debits_pence != debits:
            result.issues.append(
                Issue(
                    "contradictory_debit_summary",
                    "The statement repeats a different new-debits total.",
                )
            )


ANNOTATION_PREFIXES = ("Exchange Rate", "Nonsterling", "+")


def _is_continuation(line: _Line) -> bool:
    return (
        95 <= line.min_x <= 460
        and not line.text.upper().startswith("CR")
        and not any(line.text.startswith(prefix) for prefix in ANNOTATION_PREFIXES)
        and not ROW_PATTERN.match(line.text)
    )


def _attach_continuations(result: ParseResult, continuations, row_positions) -> None:
    """Append multiline description fragments to the row directly above them."""
    for page_number, line in continuations:
        candidates = [
            (index, y)
            for page, y, index in row_positions
            if page == page_number and 0 < y - line.y <= 14
        ]
        if not candidates:
            continue
        index, _y = min(candidates, key=lambda item: item[1] - line.y)
        row = result.rows[index]
        if line.text.strip() == row.description:
            continue
        result.rows[index] = replace(
            row,
            description=f"{row.description} {line.text}".strip(),
            source_text=f"{row.source_text} / {line.text}",
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

    if result.stated_debits_pence is not None and result.stated_debits_pence != debits:
        result.issues.append(
            Issue(
                "debit_totals_mismatch",
                f"Stated new debits {result.stated_debits_pence} pence differ from rows "
                f"{debits} pence.",
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
