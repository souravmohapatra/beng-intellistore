"""Candidate generation and reporting semantics for transfer/repayment links.

Amount equality and nearby dates are candidate signals only: they never prove
ownership or pairing, so nothing changes without a person confirming the link.
"""

from datetime import timedelta

from ledger.models import AccountKind, Transaction, TransferLink
from reporting.effects import RowEffect

CANDIDATE_WINDOW_DAYS = 7


def link_for(transaction: Transaction) -> TransferLink | None:
    for link in transaction.transfer_links_a.all():
        return link
    for link in transaction.transfer_links_b.all():
        return link
    return None


def transfer_effect(transaction: Transaction, link: TransferLink) -> RowEffect:
    if link.kind == TransferLink.Kind.TRANSFER:
        return RowEffect()
    # Card repayment: the paying current/debit entry keeps its cash outgoing;
    # the card credit only reduces debt, and neither is spending or income.
    if transaction.account.kind != AccountKind.CARD and transaction.amount_pence < 0:
        return RowEffect(cash_outgoing_pence=-transaction.amount_pence)
    return RowEffect()


def candidates_for(transaction: Transaction) -> list[dict]:
    if link_for(transaction) is not None:
        return []
    window_start = transaction.posted_on - timedelta(days=CANDIDATE_WINDOW_DAYS)
    window_end = transaction.posted_on + timedelta(days=CANDIDATE_WINDOW_DAYS)
    peers = (
        Transaction.objects.select_related("account", "upload")
        .filter(posted_on__gte=window_start, posted_on__lte=window_end)
        .exclude(pk=transaction.pk)
        .exclude(account_id=transaction.account_id)
    )
    candidates = []
    for peer in peers:
        if link_for(peer) is not None:
            continue
        pair_kind = _pair_kind(transaction, peer)
        if pair_kind is None:
            continue
        candidates.append(
            {
                "transaction": peer,
                "kind": pair_kind,
                "days_apart": abs((peer.posted_on - transaction.posted_on).days),
            }
        )
    return sorted(candidates, key=lambda item: item["days_apart"])


def _pair_kind(transaction: Transaction, peer: Transaction) -> str | None:
    kinds = {transaction.account.kind, peer.account.kind}
    if kinds == {AccountKind.CARD}:
        return None
    same_magnitude = abs(transaction.amount_pence) == abs(peer.amount_pence)
    if not same_magnitude:
        return None
    if AccountKind.CARD in kinds:
        # Repayment: the paying account is outgoing and the card credit reduces debt.
        if transaction.amount_pence < 0 and peer.amount_pence < 0:
            return TransferLink.Kind.REPAYMENT
        return None
    if transaction.amount_pence == -peer.amount_pence:
        return TransferLink.Kind.TRANSFER
    return None
