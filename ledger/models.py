"""Authoritative ledger records.

A named account is an actual bank or credit-card account identified by a
user-chosen name. Balances are not fabricated: only source evidence can produce
a known balance, so an account without observations reports unknown.
"""

from django.db import models


class AccountKind(models.TextChoices):
    CURRENT = "current", "Current account"
    CARD = "card", "Credit card"
    SAVINGS = "savings", "Savings"


class Account(models.Model):
    """A named account tracked by the application."""

    name = models.CharField(max_length=120, unique=True)
    kind = models.CharField(max_length=16, choices=AccountKind.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(kind__in=AccountKind.values),
                name="account_kind_is_supported",
            )
        ]

    def __str__(self) -> str:
        return self.name
