"""Dated balance evidence and gap-aware net-cash history.

Only dates with source-supported observations become points. No daily series is
interpolated, and long intervals without evidence are reported as coverage gaps.
"""

from dataclasses import dataclass
from datetime import date, timedelta

from ledger.models import Account, AccountKind, BalanceObservation

MAX_GAP_DAYS = 45


@dataclass(frozen=True)
class BalancePoint:
    observed_on: date
    net_cash_pence: int
    balances: list[dict]
    disputed: bool = False


@dataclass(frozen=True)
class AccountBalance:
    account: Account
    observation: BalanceObservation | None
    source: str | None
    disputed: bool = False
    alternatives: tuple = ()


def latest_balances(as_of: date) -> dict[int, AccountBalance]:
    """Latest dated balance per account, refusing to resolve contradictions.

    When several observations share the latest date with different amounts, the
    account is marked disputed and its amount is excluded from net cash.
    """
    by_account: dict[int, list[BalanceObservation]] = {}
    for observation in BalanceObservation.objects.select_related("upload").filter(
        observed_on__isnull=False, observed_on__lte=as_of
    ).order_by("account_id", "-observed_on", "-pk"):
        by_account.setdefault(observation.account_id, []).append(observation)

    result: dict[int, AccountBalance] = {}
    for account in Account.objects.all():
        observations = by_account.get(account.pk)
        if not observations:
            result[account.pk] = AccountBalance(account, None, None)
            continue
        latest_date = observations[0].observed_on
        same_day = [item for item in observations if item.observed_on == latest_date]
        amounts = {item.amount_pence for item in same_day}
        if len(amounts) > 1:
            result[account.pk] = AccountBalance(
                account,
                None,
                None,
                disputed=True,
                alternatives=tuple(
                    {
                        "amount_pence": item.amount_pence,
                        "source": item.upload.filename,
                    }
                    for item in same_day
                ),
            )
        else:
            result[account.pk] = AccountBalance(
                account, same_day[0], same_day[0].upload.filename
            )
    return result


def net_cash_history(period_start: date, period_end: date) -> list[BalancePoint]:
    dates = list(
        BalanceObservation.objects.filter(
            observed_on__gte=period_start, observed_on__lte=period_end
        )
        .values_list("observed_on", flat=True)
        .distinct()
        .order_by("observed_on")
    )
    points: list[BalancePoint] = []
    for observed_on in dates:
        latest = latest_balances(observed_on)
        total = 0
        disputed = False
        balances = []
        for account in Account.objects.order_by("name"):
            entry = latest[account.pk]
            if entry.disputed:
                disputed = True
                continue
            if entry.observation is None:
                continue
            total += (
                -entry.observation.amount_pence
                if account.kind == AccountKind.CARD
                else entry.observation.amount_pence
            )
            balances.append(
                {
                    "account": account.name,
                    "kind": account.kind,
                    "amount_pence": entry.observation.amount_pence,
                }
            )
        points.append(BalancePoint(observed_on, total, balances, disputed))
    return points


def coverage_gaps(period_start: date, period_end: date) -> list[dict]:
    gaps: list[dict] = []
    for account in Account.objects.order_by("name"):
        dates = list(
            BalanceObservation.objects.filter(
                account=account, observed_on__isnull=False
            )
            .filter(observed_on__gte=period_start, observed_on__lte=period_end)
            .order_by("observed_on")
            .values_list("observed_on", flat=True)
        )
        if not dates:
            continue
        boundaries = [period_start, *dates, period_end]
        for previous, following in zip(boundaries, boundaries[1:]):
            if (following - previous).days > MAX_GAP_DAYS:
                gaps.append(
                    {
                        "account": account.name,
                        "from": previous,
                        "to": following,
                    }
                )
    return gaps


def account_balance_rows(period_end: date) -> list[dict]:
    """Latest balance per account as of the period end, with evidence status."""
    latest = latest_balances(period_end)
    rows = []
    for account in Account.objects.order_by("name"):
        entry = latest[account.pk]
        rows.append(
            {
                "account": account,
                "observation": entry.observation,
                "source": entry.source,
                "disputed": entry.disputed,
                "alternatives": entry.alternatives,
            }
        )
    return rows


def format_pence(amount_pence: int) -> str:
    sign = "-" if amount_pence < 0 else ""
    pence = abs(amount_pence)
    return f"{sign}£{pence // 100:,}.{pence % 100:02d}"
