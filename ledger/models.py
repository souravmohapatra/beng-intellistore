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


class Original(models.Model):
    """Unchanged source bytes, content-addressed by SHA-256.

    One stored blob can support several upload receipts; each receipt keeps its
    own account association and filename.
    """

    sha256 = models.CharField(max_length=64, unique=True)
    byte_size = models.PositiveBigIntegerField()
    content_type = models.CharField(max_length=100)
    stored_path = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.sha256[:12]} ({self.byte_size} bytes)"


class Upload(models.Model):
    """A receipt for one submitted original and its selected named account."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        UNSUPPORTED = "unsupported", "Unsupported"

    original = models.ForeignKey(
        Original, on_delete=models.PROTECT, related_name="uploads"
    )
    account = models.ForeignKey(
        Account, on_delete=models.PROTECT, related_name="uploads"
    )
    filename = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    review_note = models.TextField(blank=True)
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-received_at", "-pk"]

    def __str__(self) -> str:
        return f"{self.filename} → {self.account}"
