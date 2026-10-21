"""Transaction-level evidence for search and metric drill-down."""

from datetime import date

from ledger.models import AccountKind, Transaction
from reporting.history import format_pence
from reporting.totals import classify

METRIC_LABELS = {
    "spending": "Spending",
    "income": "Income",
    "cash_outgoing": "Cash outgoing",
}
PAGE_SIZE = 50


def metric_entries(metric: str, period_start: date, period_end: date):
    """Return contributing rows, their total, and exclusions for one metric."""
    entries = []
    unclassified = 0
    other = 0
    total = 0

    rows = (
        Transaction.objects.select_related("account", "upload")
        .filter(posted_on__gte=period_start, posted_on__lte=period_end)
        .order_by("posted_on", "pk")
    )
    for transaction in rows:
        effect = classify(transaction)
        if effect is None:
            unclassified += 1
            continue
        contribution = getattr(effect, f"{metric}_pence")
        if not contribution:
            other += 1
            continue
        total += contribution
        entries.append(
            {
                "transaction": transaction,
                "contribution_pence": contribution,
                "contribution_display": format_pence(contribution),
                "explanation": _explain(metric, transaction),
            }
        )
    return entries, total, {"unclassified": unclassified, "other": other}


def _explain(metric: str, transaction: Transaction) -> str:
    description = transaction.description.upper()
    kind = transaction.account.kind
    if metric == "spending":
        if transaction.amount_pence > 0 and kind == AccountKind.CARD:
            return "Card purchase increases card debt"
        if "REFUND" in description:
            return "Refund reverses spending in this period"
        if transaction.transaction_type == "Exchange":
            return "GBP converted back reduces spending" if transaction.amount_pence > 0 else "GBP converted out counts as spending"
        if transaction.transaction_type == "Cash withdrawal":
            return "Cash withdrawal is spending and cash outgoing"
        return "Purchase or charge"
    if metric == "income":
        return "Identified salary or interest"
    if metric == "cash_outgoing":
        return "Cash leaving a current/debit account"
    return ""


def search_transactions(query: str, period_start=None, period_end=None):
    """Match the original description text only, newest first."""
    rows = Transaction.objects.select_related("account", "upload").filter(
        description__icontains=query
    )
    if period_start is not None and period_end is not None:
        rows = rows.filter(posted_on__gte=period_start, posted_on__lte=period_end)
    return rows.order_by("-posted_on", "-pk")
