"""Deterministic interpretation of the supported Lloyds Current layout.

Supported layout contract, established from the supplied statement's observed
structure and exercised by synthetic fixtures:

- header text contains ``Lloyds Bank``, ``CURRENT.`` and ``Your Transactions``;
- ``01 August 2026 to 31 August 2026.`` gives the statement period;
- ``Money In.`` / ``Money Out.`` / ``Balance on <date>.`` summaries precede the
  transactions;
- each transaction is a vertical block of labels and values: ``Date``,
  ``Description``, ``Type``, ``Money In (£)``, ``Money Out (£)``, ``Balance (£)``,
  with ``blank.`` in the unused money column;
- accessibility labels such as ``Column`` are interleaved and are ignored.

Direction comes from which money column carries a value and is validated against
the running-balance delta. Nothing is guessed: a malformed or contradictory row
fails validation instead of producing a financial fact.
"""

import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

LAYOUT_BANK = "Lloyds Bank"
LAYOUT_KIND = "CURRENT."
ACCOUNT_KIND_HINT = "current"

PERIOD_PATTERN = re.compile(
    r"(\d{2} [A-Z][a-z]+ \d{4})\s+to\s+(\d{2} [A-Z][a-z]+ \d{4})"
)
BALANCE_ON_PATTERN = re.compile(r"^Balance on (\d{2} [A-Z][a-z]+ \d{4})$")
AMOUNT_PATTERN = re.compile(r"^£?([\d,]+\.\d{2})$")
DATE_PATTERN = re.compile(r"^\d{2} [A-Z][a-z]{2} \d{2}$")

NOISE_LINES = {"Column"}
NOISE_PREFIXES = ("Page ",)


@dataclass(frozen=True)
class ParsedTransaction:
    posted_on: date
    description: str
    transaction_type: str
    amount_pence: int
    balance_pence: int
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
class ParseResult:
    recognised: bool
    account_kind_hint: str | None = None
    rows: list[ParsedTransaction] | None = None
    balances: list[BalanceAnchor] | None = None
    issues: list[Issue] | None = None
    reconciled: bool = False
    opening_pence: int | None = None
    closing_pence: int | None = None
    money_in_pence: int | None = None
    money_out_pence: int | None = None

    def __post_init__(self):
        self.rows = [] if self.rows is None else self.rows
        self.balances = [] if self.balances is None else self.balances
        self.issues = [] if self.issues is None else self.issues


def to_pence(text: str) -> int:
    match = AMOUNT_PATTERN.match(text.strip())
    if match is None:
        raise InvalidOperation(text)
    pence = Decimal(match.group(1).replace(",", "")) * 100
    if pence != pence.to_integral_value():
        raise InvalidOperation(text)
    return int(pence)


def parse(text: str) -> ParseResult:
    """Interpret statement text; pages are separated by form feeds."""
    pages = text.split("\f")
    if (
        not pages
        or LAYOUT_BANK not in pages[0]
        or LAYOUT_KIND not in pages[0]
        or "Your Transactions" not in "\n".join(pages)
    ):
        return ParseResult(recognised=False)

    result = ParseResult(recognised=True, account_kind_hint=ACCOUNT_KIND_HINT)
    period_start, period_end = _period(pages[0], result.issues)
    running_balance: int | None = None
    block: dict | None = None

    for page_number, page_text in enumerate(pages, start=1):
        lines = [line.strip() for line in page_text.splitlines()]
        index = 0
        while index < len(lines):
            line = lines[index]
            index += 1
            if not line or line in NOISE_LINES or line.startswith(NOISE_PREFIXES):
                continue
            if line.endswith("."):
                line = line[:-1].strip()

            if line == "Date":
                value, index = _next_value(lines, index)
                if value is None or not DATE_PATTERN.match(value):
                    continue  # table header, not a transaction block
                block = {"page": page_number, "date": value}
                continue

            if line == "Description" and block is not None:
                block["description"], index = _next_value(lines, index)
                continue
            if line == "Type" and block is not None:
                block["type"], index = _next_value(lines, index)
                continue
            if line == "Money In (£)" and block is not None:
                block["money_in"], index = _next_value(lines, index)
                continue
            if line == "Money Out (£)" and block is not None:
                block["money_out"], index = _next_value(lines, index)
                continue
            if line == "Balance (£)" and block is not None:
                block["balance"], index = _next_value(lines, index)
                block, running_balance = _finish_block(
                    block, period_start, period_end, running_balance, result
                )
                continue

            if line == "Money In":
                value, index = _next_value(lines, index)
                if value is not None:
                    result.money_in_pence = _maybe_pence(value)
                continue
            if line == "Money Out":
                value, index = _next_value(lines, index)
                if value is not None:
                    result.money_out_pence = _maybe_pence(value)
                continue
            balance_on = BALANCE_ON_PATTERN.match(line)
            if balance_on:
                value, index = _next_value(lines, index)
                amount = _maybe_pence(value) if value is not None else None
                if amount is None:
                    continue
                observed = _parse_statement_date(balance_on.group(1))
                if observed == period_start:
                    result.opening_pence = amount
                    result.balances.append(BalanceAnchor("opening", amount, observed))
                    if running_balance is None:
                        running_balance = amount
                elif observed == period_end:
                    result.closing_pence = amount
                    result.balances.append(BalanceAnchor("closing", amount, observed))
                else:
                    result.issues.append(
                        Issue(
                            "unexpected_balance_date",
                            f"Balance anchor dated {observed} is neither period end.",
                        )
                    )

    _validate(result)
    return result


def _period(first_page: str, issues: list[Issue]):
    match = PERIOD_PATTERN.search(first_page)
    if match is None:
        issues.append(Issue("missing_period", "The statement period was not found."))
        return None, None
    return _parse_statement_date(match.group(1)), _parse_statement_date(match.group(2))


def _parse_statement_date(text: str) -> date:
    return datetime.strptime(" ".join(text.split()), "%d %B %Y").date()


def _next_value(lines: list[str], index: int) -> tuple[str | None, int]:
    """Return the value line following a label, skipping accessibility filler."""
    while index < len(lines):
        candidate = lines[index]
        index += 1
        if not candidate or candidate in NOISE_LINES or candidate.startswith(NOISE_PREFIXES):
            continue
        return candidate.rstrip(".").strip(), index
    return None, index


def _maybe_pence(value: str) -> int | None:
    try:
        return to_pence(value)
    except InvalidOperation:
        return None


def _finish_block(
    block: dict,
    period_start: date | None,
    period_end: date | None,
    running_balance: int | None,
    result: ParseResult,
) -> tuple[None, int | None]:
    page_number = block["page"]
    try:
        posted_on = datetime.strptime(block["date"], "%d %b %y").date()
    except (KeyError, ValueError):
        result.issues.append(
            Issue("malformed_transaction_row", f"Unreadable date on page {page_number}.")
        )
        return None, running_balance

    balance = _maybe_pence(block.get("balance") or "")
    if balance is None:
        result.issues.append(
            Issue(
                "malformed_transaction_row",
                f"Unreadable balance for the {posted_on.isoformat()} row on page {page_number}.",
            )
        )
        return None, running_balance

    money_in = _maybe_pence(block.get("money_in") or "blank")
    money_out = _maybe_pence(block.get("money_out") or "blank")
    if money_in and money_out:
        result.issues.append(
            Issue(
                "malformed_transaction_row",
                f"Row dated {posted_on.isoformat()} carries both a money-in and money-out value.",
            )
        )
        return None, running_balance
    if money_in is None and money_out is None:
        result.issues.append(
            Issue(
                "malformed_transaction_row",
                f"Row dated {posted_on.isoformat()} has no readable amount.",
            )
        )
        return None, running_balance

    amount_pence = money_in if money_in is not None else -money_out

    if period_start and period_end and not (period_start <= posted_on <= period_end):
        result.issues.append(
            Issue(
                "date_outside_period",
                f"Row dated {posted_on.isoformat()} is outside the statement period.",
            )
        )

    if running_balance is None:
        result.issues.append(
            Issue("missing_opening_balance", "No opening balance precedes the transaction rows.")
        )
    elif balance - running_balance != amount_pence:
        result.issues.append(
            Issue(
                "running_balance_mismatch",
                f"Row dated {posted_on.isoformat()} states {amount_pence} pence but "
                f"changes the balance by {balance - running_balance} pence.",
            )
        )

    result.rows.append(
        ParsedTransaction(
            posted_on=posted_on,
            description=block.get("description") or "",
            transaction_type=block.get("type") or "",
            amount_pence=amount_pence,
            balance_pence=balance,
            page=page_number,
            row=sum(1 for row in result.rows if row.page == page_number) + 1,
            source_text=(
                f"Date {block['date']}; Description {block.get('description') or ''}; "
                f"Type {block.get('type') or ''}; Money In {block.get('money_in') or 'blank'}; "
                f"Money Out {block.get('money_out') or 'blank'}; Balance {block.get('balance')}"
            ),
        )
    )
    return None, balance


def _validate(result: ParseResult) -> None:
    if result.opening_pence is None:
        result.issues.append(Issue("missing_opening_balance", "No opening balance was found."))
    if result.closing_pence is None:
        result.issues.append(Issue("missing_closing_balance", "No closing balance was found."))

    money_in = sum(row.amount_pence for row in result.rows if row.amount_pence > 0)
    money_out = -sum(row.amount_pence for row in result.rows if row.amount_pence < 0)

    if result.money_in_pence is not None and result.money_in_pence != money_in:
        result.issues.append(
            Issue(
                "totals_mismatch",
                f"Stated money in {result.money_in_pence} pence differs from rows {money_in} pence.",
            )
        )
    if result.money_out_pence is not None and result.money_out_pence != money_out:
        result.issues.append(
            Issue(
                "totals_mismatch",
                f"Stated money out {result.money_out_pence} pence differs from rows {money_out} pence.",
            )
        )

    if result.opening_pence is not None and result.closing_pence is not None:
        expected_close = result.opening_pence + sum(row.amount_pence for row in result.rows)
        if expected_close != result.closing_pence:
            result.issues.append(
                Issue(
                    "closing_balance_mismatch",
                    f"Opening plus rows gives {expected_close} pence, "
                    f"not the stated {result.closing_pence} pence.",
                )
            )

    result.reconciled = not result.issues
