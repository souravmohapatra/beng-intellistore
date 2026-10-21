"""Reporting effects shared by totals and transfer semantics."""

from dataclasses import dataclass


@dataclass
class RowEffect:
    spending_pence: int = 0
    income_pence: int = 0
    cash_outgoing_pence: int = 0
