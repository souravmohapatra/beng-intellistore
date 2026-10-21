"""Deterministic interpretation of the consolidated Revolut export.

Supported slice: the personal GBP current account. The same original also
contains personal USD/SEK, joint GBP, savings and crypto sections; those are
reported as ignored (or deferred for savings, which the next ticket implements)
and never contribute GBP transactions.

Rows are positioned fragments: date at the left, description, category, signed
``£`` amount, running balance, tax withheld, other taxes and fees in columns.
Description continuations sit directly below the row. Amounts carrying ``$`` or
``SEK`` belong to excluded sections and are not accepted as GBP facts.
"""

import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

SECTION_NAME = "revolut_personal_gbp"
ACCOUNT_KIND_HINT = "current"

DATE_PATTERN = re.compile(r"^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4}$")
PERIOD_PATTERN = re.compile(
    r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4})"
    r"\s*-\s*"
    r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4})"
)
GBP_AMOUNT = re.compile(r"^(-?)£([\d,]+\.\d{2})$")
PERSONAL_GBP = "Personal Account (GBP)"
TRANSACTION_HEADING = "Transaction statement"
SUMMARY_HEADING = "Current Accounts Summaries"
SAVINGS_HEADING = "Savings Accounts Summaries"
SAVINGS_TRANSACTIONS = "Savings Accounts Transaction Statements"
SAVINGS_DATE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{2})$")
CRYPTO_HEADING = "Crypto Summaries"

EXCLUDED_SECTIONS = (
    ("personal_account_usd", PERSONAL_GBP.replace("GBP", "USD"), "ignored"),
    ("personal_account_sek", PERSONAL_GBP.replace("GBP", "SEK"), "ignored"),
    ("joint_account_gbp", "Joint Account (GBP)", "ignored"),
    ("crypto", CRYPTO_HEADING, "ignored"),
)
EXCLUSION_REASONS = {
    "ignored": "Excluded section: only personal GBP is in scope.",
    "deferred": "Savings support is not implemented yet; this section was not imported.",
}


@dataclass(frozen=True)
class ParsedTransaction:
    posted_on: date
    description: str
    transaction_type: str
    amount_pence: int
    balance_pence: int | None
    page: int
    row: int
    source_text: str


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
class SavingsResult:
    recognised: bool = False
    rows: list[ParsedTransaction] | None = None
    balances: list[BalanceAnchor] | None = None
    issues: list[Issue] | None = None
    review_notes: list[Issue] | None = None

    def __post_init__(self):
        self.rows = [] if self.rows is None else self.rows
        self.balances = [] if self.balances is None else self.balances
        self.issues = [] if self.issues is None else self.issues
        self.review_notes = [] if self.review_notes is None else self.review_notes


@dataclass
class ParseResult:
    recognised: bool
    section_name: str = SECTION_NAME
    account_kind_hint: str | None = None
    rows: list[ParsedTransaction] | None = None
    balances: list[BalanceAnchor] | None = None
    issues: list[Issue] | None = None
    excluded_sections: list[dict] | None = None
    savings: SavingsResult | None = None
    reconciled: bool = False
    opening_pence: int | None = None
    closing_pence: int | None = None
    money_in_pence: int | None = None
    money_out_pence: int | None = None

    def __post_init__(self):
        self.rows = [] if self.rows is None else self.rows
        self.balances = [] if self.balances is None else self.balances
        self.issues = [] if self.issues is None else self.issues
        self.excluded_sections = (
            [] if self.excluded_sections is None else self.excluded_sections
        )


def parse_pages(pages: list[list[tuple[float, float, str]]]) -> ParseResult:
    page_texts = [_page_text(page) for page in pages]
    if not any("Custom Statement" in text for text in page_texts):
        return ParseResult(recognised=False)
    if not any(PERSONAL_GBP in text for text in page_texts):
        return ParseResult(recognised=False)

    result = ParseResult(recognised=True, account_kind_hint=ACCOUNT_KIND_HINT)
    period_start, period_end = _statement_period(page_texts)
    result.excluded_sections = [
        {"name": name, "heading": heading, "status": status, "reason": EXCLUSION_REASONS[status]}
        for name, heading, status in EXCLUDED_SECTIONS
        if any(heading in text for text in page_texts)
    ]

    savings = SavingsResult(recognised=any(SAVINGS_HEADING in text for text in page_texts))
    for page_number, tokens in enumerate(pages, start=1):
        text = page_texts[page_number - 1]
        if PERSONAL_GBP in text:
            if TRANSACTION_HEADING in text:
                _parse_transaction_page(tokens, page_number, result)
            elif SUMMARY_HEADING in text:
                _parse_summary_page(tokens, result, period_start, period_end)
        if savings.recognised:
            if SAVINGS_TRANSACTIONS in text:
                _parse_savings_transactions(tokens, page_number, period_start, period_end, savings)
            elif SAVINGS_HEADING in text:
                _parse_savings_summary(tokens, period_start, period_end, savings)

    if savings.recognised:
        _validate_savings(savings)
        result.savings = savings

    _validate(result)
    return result


def _page_text(tokens) -> str:
    return " ".join(text for _x, _y, text in tokens)


def _statement_period(page_texts) -> tuple[date | None, date | None]:
    for text in page_texts:
        match = PERIOD_PATTERN.search(text)
        if not match:
            continue
        try:
            return (
                datetime.strptime(" ".join(match.group(1).split()), "%b %d, %Y").date(),
                datetime.strptime(" ".join(match.group(2).split()), "%b %d, %Y").date(),
            )
        except ValueError:
            return None, None
    return None, None


def _parse_savings_summary(tokens, period_start, period_end, savings: SavingsResult) -> None:
    for _y, text in _lines(tokens):
        if text.startswith("Opening balance"):
            amount = _trailing_amount(text)
            if amount is not None and not any(b.kind == "opening" for b in savings.balances):
                savings.balances.append(BalanceAnchor("opening", amount, period_start))
        elif text.startswith("Closing balance"):
            amount = _trailing_amount(text)
            if amount is not None and not any(b.kind == "closing" for b in savings.balances):
                savings.balances.append(BalanceAnchor("closing", amount, period_end))


def _parse_savings_transactions(tokens, page_number, period_start, period_end, savings: SavingsResult) -> None:
    for x, y, text in sorted(tokens, key=lambda token: -token[1]):
        if x > 70:
            continue
        match = SAVINGS_DATE.match(text.strip())
        if not match:
            continue
        month, day, year = (int(part) for part in match.groups())
        try:
            posted = date(2000 + year, month, day)
        except ValueError:
            savings.issues.append(
                Issue("invalid_transaction_date", f"Unreadable savings date on page {page_number}.")
            )
            continue
        if period_start and period_end and not (period_start <= posted <= period_end):
            savings.issues.append(
                Issue("date_outside_period", f"Savings row {posted} is outside the period.")
            )
            continue
        net = next(
            (
                _gbp_pence(value)
                for tx, ty, value in tokens
                if tx >= 500 and abs(ty - y) <= 3.0
            ),
            None,
        )
        if net is None:
            savings.issues.append(
                Issue("malformed_transaction_row", f"Unreadable net interest on page {page_number}.")
            )
            continue
        savings.rows.append(
            ParsedTransaction(
                posted_on=posted,
                description="Gross Interest",
                transaction_type="Interest",
                amount_pence=net,
                balance_pence=None,
                page=page_number,
                row=sum(1 for row in savings.rows if row.page == page_number) + 1,
                source_text=f"{text} Gross Interest {net}",
            )
        )


def _validate_savings(savings: SavingsResult) -> None:
    opening = next((b for b in savings.balances if b.kind == "opening"), None)
    closing = next((b for b in savings.balances if b.kind == "closing"), None)
    if opening is None:
        savings.issues.append(Issue("missing_opening_balance", "No savings opening balance was found."))
    if closing is None:
        savings.issues.append(Issue("missing_closing_balance", "No savings closing balance was found."))
    if opening is not None and closing is not None:
        expected = opening.amount_pence + sum(row.amount_pence for row in savings.rows)
        if expected != closing.amount_pence:
            savings.review_notes.append(
                Issue(
                    "unexplained_savings_change",
                    "Savings balances changed beyond the listed interest; principal movements "
                    "are not evidenced by this export.",
                )
            )


def _parse_summary_page(tokens, result: ParseResult, period_start, period_end) -> None:
    for _y, text in _lines(tokens):
        if text.startswith("Opening balance") and result.opening_pence is None:
            amount = _trailing_amount(text)
            if amount is not None:
                result.opening_pence = amount
                result.balances.append(BalanceAnchor("opening", amount, period_start))
        elif text.startswith("Closing balance") and result.closing_pence is None:
            amount = _trailing_amount(text)
            if amount is not None:
                result.closing_pence = amount
                result.balances.append(BalanceAnchor("closing", amount, period_end))


def _trailing_amount(text: str) -> int | None:
    match = re.search(r"(-?£[\d,]+\.\d{2})$", text)
    return _gbp_pence(match.group(1)) if match else None


def _parse_transaction_page(tokens, page_number: int, result: ParseResult) -> None:
    date_tokens = [
        (x, y, text)
        for x, y, text in tokens
        if x <= 80 and DATE_PATTERN.match(text.strip())
    ]
    date_tokens.sort(key=lambda item: -item[1])
    continuations = [
        (x, y, text)
        for x, y, text in tokens
        if 110 <= x <= 250 and not DATE_PATTERN.match(text.strip())
    ]

    for _x, y, date_text in date_tokens:
        row_tokens = [token for token in tokens if abs(token[1] - y) <= 3.0]
        cells = {name: "" for name in ("description", "category", "money", "balance", "tax", "other", "fees")}
        for tx, _ty, text in sorted(row_tokens, key=lambda token: token[0]):
            if tx <= 80:
                continue
            if tx < 250:
                cells["description"] += (" " if cells["description"] else "") + text.strip()
            elif tx < 335:
                cells["category"] += (" " if cells["category"] else "") + text.strip()
            elif tx < 380:
                cells["money"] = text.strip()
            elif tx < 425:
                cells["balance"] = text.strip()
            elif tx < 465:
                cells["tax"] = text.strip()
            elif tx < 520:
                cells["other"] = text.strip()
            else:
                cells["fees"] = text.strip()

        # Description fragments belonging to this row sit just below it.
        wrapped = sorted(
            (ty, text.strip())
            for _tx, ty, text in continuations
            if 0 < y - ty <= 16 and text.strip()
        )
        for _ty, fragment in sorted(wrapped, reverse=True):
            if fragment != cells["description"]:
                cells["description"] += (" " if cells["description"] else "") + fragment

        try:
            posted = datetime.strptime(" ".join(date_text.split()), "%b %d, %Y").date()
        except ValueError:
            result.issues.append(
                Issue("invalid_transaction_date", f"Unreadable date on page {page_number}.")
            )
            continue

        amount = _gbp_pence(cells["money"])
        balance = _gbp_pence(cells["balance"])
        if amount is None:
            result.issues.append(
                Issue(
                    "malformed_transaction_row",
                    f"Unreadable GBP amount on page {page_number} for {posted.isoformat()}.",
                )
            )
            continue
        if balance is None:
            result.issues.append(
                Issue(
                    "malformed_transaction_row",
                    f"Unreadable balance on page {page_number} for {posted.isoformat()}.",
                )
            )
            continue

        result.rows.append(
            ParsedTransaction(
                posted_on=posted,
                description=cells["description"] or "Unknown",
                transaction_type=cells["category"],
                amount_pence=amount,
                balance_pence=balance,
                page=page_number,
                row=sum(1 for row in result.rows if row.page == page_number) + 1,
                source_text=(
                    f"{date_text} {cells['description']} {cells['category']} "
                    f"{cells['money']} {cells['balance']}"
                ).strip(),
            )
        )



def _lines(tokens) -> list[tuple[float, str]]:
    grouped: dict[float, list[tuple[float, str]]] = {}
    for x, y, text in tokens:
        if text.strip():
            grouped.setdefault(round(y, 1), []).append((x, text.strip()))
    return [
        (y, " ".join(text for _x, text in sorted(grouped[y])))
        for y in sorted(grouped, reverse=True)
    ]


def _gbp_pence(text: str) -> int | None:
    match = GBP_AMOUNT.match((text or "").strip())
    if not match:
        return None
    try:
        value = Decimal(match.group(2).replace(",", "")) * 100
    except InvalidOperation:
        return None
    if value != value.to_integral_value():
        return None
    pence = int(value)
    return -pence if match.group(1) else pence


def _validate(result: ParseResult) -> None:
    if result.opening_pence is None:
        result.issues.append(Issue("missing_opening_balance", "No opening balance was found."))
    if result.closing_pence is None:
        result.issues.append(Issue("missing_closing_balance", "No closing balance was found."))
    if not result.rows:
        result.issues.append(Issue("no_transactions", "No personal GBP rows were found."))

    previous = result.opening_pence
    for row in result.rows:
        if previous is not None and row.balance_pence - previous != row.amount_pence:
            result.issues.append(
                Issue(
                    "running_balance_mismatch",
                    f"{row.posted_on.isoformat()} states {row.amount_pence} pence but changes "
                    f"the balance by {row.balance_pence - previous} pence.",
                )
            )
        previous = row.balance_pence

    money_in = sum(row.amount_pence for row in result.rows if row.amount_pence > 0)
    money_out = -sum(row.amount_pence for row in result.rows if row.amount_pence < 0)
    if result.money_in_pence is not None and result.money_in_pence != money_in:
        result.issues.append(
            Issue("totals_mismatch", "Stated money in differs from the rows.")
        )
    if result.money_out_pence is not None and result.money_out_pence != money_out:
        result.issues.append(
            Issue("totals_mismatch", "Stated money out differs from the rows.")
        )

    if result.opening_pence is not None and result.closing_pence is not None:
        expected = result.opening_pence + sum(row.amount_pence for row in result.rows)
        if expected != result.closing_pence:
            result.issues.append(
                Issue(
                    "closing_balance_mismatch",
                    f"Opening plus rows gives {expected} pence, not "
                    f"{result.closing_pence} pence.",
                )
            )

    result.reconciled = not result.issues
