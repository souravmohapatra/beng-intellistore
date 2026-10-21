"""Posting-period reporting totals.

Classification is deterministic and independent of any model advice. Rows whose
classification is not established contribute to no total; affected totals are
marked provisional rather than guessed. Money is integer pence throughout.

Semantics follow the release specification: card purchases are spending but not
cash outgoing until repaid; card repayments and own-account transfers are not
new spending or income; refunds reduce spending in their posting period; savings
interest is income; a cash withdrawal is spending and outgoing.
"""

from dataclasses import dataclass, field
from datetime import date

from ledger.models import Account, AccountKind, BalanceObservation, Transaction
from reporting.history import latest_balances


@dataclass
class RowEffect:
    spending_pence: int = 0
    income_pence: int = 0
    cash_outgoing_pence: int = 0


@dataclass
class TotalsReport:
    period_start: date
    period_end: date
    spending_pence: int = 0
    income_pence: int = 0
    cash_outgoing_pence: int = 0
    net_cash_pence: int | None = None
    provisional: bool = False
    unclassified: int = 0
    net_cash_provisional: bool = False
    missing_balance_accounts: list[str] = field(default_factory=list)
    disputed_balance_accounts: list[str] = field(default_factory=list)
    balances_used: list[dict] = field(default_factory=list)
    currency: str = "GBP"
    has_evidence: bool = False


SPENDING_TYPES = {
    "Merchant",
    "Card payment",
    "DD",
    "Direct debit",
    "Cash withdrawal",
}
CARD_REPAYMENT_MARKERS = ("PAYMENT RECEIVED", "DIRECT DEBIT PAYMENT", "PAYMENT - THANK YOU")
REFUND_TYPES = {"Refund"}
IDENTIFIED_INCOME_TYPES = {"Salary", "Interest"}


def classify(transaction: Transaction) -> RowEffect | None:
    """Confirmed corrections take precedence over machine-derived effects."""
    correction = active_correction(transaction)
    if correction is not None:
        return effect_for_classification(correction.classification, transaction)
    return classify_source(transaction)


def classify_source(transaction: Transaction) -> RowEffect | None:
    """Machine-derived reporting effect, or None when the evidence is unresolved."""
    amount = transaction.amount_pence
    kind = transaction.account.kind
    description = transaction.description.upper()
    transaction_type = transaction.transaction_type.strip()

    if kind == AccountKind.CARD:
        if amount > 0:
            return RowEffect(spending_pence=amount)
        if any(marker in description for marker in CARD_REPAYMENT_MARKERS):
            return RowEffect()
        if "REFUND" in description:
            # Card credits are already negative debt movements; the refund
            # reverses spending without a second sign flip.
            return RowEffect(spending_pence=amount)
        # A card credit without repayment or refund evidence is not classified.
        return None

    if kind == AccountKind.SAVINGS:
        if transaction_type in IDENTIFIED_INCOME_TYPES and amount > 0:
            return RowEffect(income_pence=amount)
        return None

    # Current/debit accounts.
    if transaction_type in REFUND_TYPES or "REFUND" in description:
        return RowEffect(spending_pence=-amount) if amount > 0 else None
    if transaction_type in IDENTIFIED_INCOME_TYPES or (
        amount > 0 and "SALARY" in description
    ):
        return RowEffect(income_pence=amount) if amount > 0 else None
    if transaction_type == "Exchange" and "EXCHANGED TO" in description:
        if "EXCHANGED TO GBP" in description:
            # Currency converted back into GBP reduces spending in its period.
            return RowEffect(spending_pence=-amount) if amount > 0 else None
        # GBP converted out is spending and outgoing; the foreign leg is ignored.
        return RowEffect(spending_pence=-amount, cash_outgoing_pence=-amount) if amount < 0 else None
    if transaction_type in SPENDING_TYPES:
        if amount < 0:
            return RowEffect(spending_pence=-amount, cash_outgoing_pence=-amount)
        return None
    return None


def active_correction(transaction):
    """Latest non-reverted correction; works with prefetched corrections."""
    active = [item for item in transaction.corrections.all() if item.reverted_at is None]
    return active[-1] if active else None


def classification_applies(classification: str, transaction: Transaction) -> bool:
    """A confirmation must agree with the source's signed direction."""
    amount = transaction.amount_pence
    kind = transaction.account.kind
    if classification == "spending":
        return amount < 0 if kind != AccountKind.CARD else amount > 0
    if classification == "income":
        return amount > 0 and kind != AccountKind.CARD
    if classification == "refund":
        return amount > 0 if kind != AccountKind.CARD else amount < 0
    if classification in {"transfer", "unknown"}:
        return True
    return False


def effect_for_classification(classification: str, transaction: Transaction) -> RowEffect | None:
    """Translate a confirmed classification into reporting effects.

    Only valid directions are translated; callers check applicability first.
    """
    amount = transaction.amount_pence
    kind = transaction.account.kind
    if classification == "spending":
        if kind == AccountKind.CARD:
            return RowEffect(spending_pence=amount)
        return RowEffect(spending_pence=-amount, cash_outgoing_pence=-amount)
    if classification == "income":
        return RowEffect(income_pence=amount)
    if classification == "refund":
        return RowEffect(spending_pence=-amount)
    if classification == "transfer":
        return RowEffect()
    return None


def compute_totals(period_start: date, period_end: date) -> TotalsReport:
    report = TotalsReport(period_start=period_start, period_end=period_end)

    rows = (
        Transaction.objects.select_related("account")
        .prefetch_related("corrections")
        .filter(posted_on__gte=period_start, posted_on__lte=period_end)
    )
    for row in rows:
        effect = classify(row)
        if effect is None:
            report.unclassified += 1
            report.provisional = True
            continue
        report.spending_pence += effect.spending_pence
        report.income_pence += effect.income_pence
        report.cash_outgoing_pence += effect.cash_outgoing_pence

    (
        report.net_cash_pence,
        report.missing_balance_accounts,
        report.disputed_balance_accounts,
        report.balances_used,
    ) = _net_cash(period_end)
    report.net_cash_provisional = bool(
        report.missing_balance_accounts or report.disputed_balance_accounts
    )
    report.has_evidence = bool(report.balances_used) or Transaction.objects.filter(
        posted_on__gte=period_start, posted_on__lte=period_end
    ).exists()
    return report


def _net_cash(period_end: date):
    accounts = Account.objects.order_by("name")
    latest = latest_balances(period_end)
    total = 0
    missing: list[str] = []
    disputed: list[str] = []
    used: list[dict] = []

    for account in accounts:
        entry = latest[account.pk]
        if entry.disputed:
            disputed.append(account.name)
            continue
        observation = entry.observation
        if observation is None:
            missing.append(account.name)
            continue
        if account.kind == AccountKind.CARD:
            total -= observation.amount_pence
        else:
            total += observation.amount_pence
        used.append(
            {
                "account": account.name,
                "kind": account.kind,
                "amount_pence": observation.amount_pence,
                "observed_on": observation.observed_on,
            }
        )
    if not used:
        return None, missing, disputed, used
    return total, missing, disputed, used
