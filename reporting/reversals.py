"""Candidate generation and semantics for evidenced reversals.

Opposite amount and nearby dates are candidate signals only; a person must
confirm the reversal, and an unmatched return stays unresolved rather than
becoming income.
"""

from datetime import timedelta

from ledger.models import Transaction, TransferLink
from reporting.effects import RowEffect

# Cross-statement reversals routinely arrive in a later period; this window
# only decides which pairs are offered, never that a reversal happened.
CANDIDATE_WINDOW_DAYS = 45
REVERSAL_HINTS = ("REFUND", "REVERSAL", "RETURN", "WAIVER", "CHARGEBACK", "REVERSED")


def reversal_for(transaction: Transaction):
    link = getattr(transaction, "reversal_link", None)
    return link


def reversal_effect(transaction: Transaction, original: Transaction) -> RowEffect:
    from reporting.totals import classify

    base = classify(original) or RowEffect()
    return RowEffect(
        spending_pence=-base.spending_pence,
        income_pence=-base.income_pence,
    )


def candidates_for(transaction: Transaction) -> list[dict]:
    if reversal_for(transaction) is not None:
        return []
    if Transaction.objects.filter(reversal_link__reverses=transaction).exists():
        return []  # already reversed elsewhere
    window_start = transaction.posted_on - timedelta(days=CANDIDATE_WINDOW_DAYS)
    window_end = transaction.posted_on + timedelta(days=CANDIDATE_WINDOW_DAYS)
    peers = (
        Transaction.objects.select_related("account", "upload")
        .filter(
            account_id=transaction.account_id,
            posted_on__gte=window_start,
            posted_on__lte=window_end,
            amount_pence=-transaction.amount_pence,
        )
        .exclude(pk=transaction.pk)
        .exclude(reversal_link__isnull=False)
        .exclude(transfer_links_a__isnull=False)
        .exclude(transfer_links_b__isnull=False)
        .exclude(duplicate_matches__isnull=False)
    )
    hint = _has_hint(transaction.description)
    candidates = []
    for peer in peers:
        if not hint and not _has_hint(peer.description):
            continue
        if peer.account.kind == transaction.account.kind:
            candidates.append(
                {
                    "transaction": peer,
                    "days_apart": abs((peer.posted_on - transaction.posted_on).days),
                }
            )
    return sorted(candidates, key=lambda item: item["days_apart"])


def reversal_direction(left: Transaction, right: Transaction):
    """Identify (reversal_row, original_row), refusing ambiguous directions."""
    left_hint = _has_hint(left.description)
    right_hint = _has_hint(right.description)
    if left_hint and not right_hint:
        return left, right
    if right_hint and not left_hint:
        return right, left
    if left_hint and right_hint and left.posted_on != right.posted_on:
        return (left, right) if left.posted_on > right.posted_on else (right, left)
    return None


def _has_hint(description: str) -> bool:
    upper = description.upper()
    return any(hint in upper for hint in REVERSAL_HINTS)
