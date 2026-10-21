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
        IMPORTED = "imported", "Imported"
        DUPLICATE = "duplicate", "Duplicate (already imported)"
        NEEDS_REVIEW = "needs_review", "Needs review"

    original = models.ForeignKey(
        Original, on_delete=models.PROTECT, related_name="uploads"
    )
    account = models.ForeignKey(
        Account, on_delete=models.PROTECT, related_name="uploads"
    )
    # Confirmed secondary mapping for consolidated sources (e.g. Revolut savings).
    savings_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="savings_uploads",
        null=True,
        blank=True,
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


class Transaction(models.Model):
    """An account-specific financial record derived from one source row."""

    account = models.ForeignKey(
        Account, on_delete=models.PROTECT, related_name="transactions"
    )
    upload = models.ForeignKey(
        Upload, on_delete=models.PROTECT, related_name="transactions"
    )
    posted_on = models.DateField(db_index=True)
    source_transaction_date = models.DateField(null=True, blank=True)
    description = models.TextField()
    transaction_type = models.CharField(max_length=60, blank=True)
    amount_pence = models.IntegerField()
    balance_pence = models.IntegerField(null=True, blank=True)
    source_page = models.PositiveIntegerField()
    source_row = models.PositiveIntegerField()
    source_text = models.TextField()
    needs_review = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["posted_on", "pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["upload", "source_page", "source_row"],
                name="unique_source_row_per_upload",
            )
        ]

    def __str__(self) -> str:
        return f"{self.posted_on} {self.description} ({self.amount_pence})"

    @property
    def amount_display(self) -> str:
        return _format_pence(self.amount_pence)

    @property
    def source_date_display(self) -> str:
        return "" if self.source_transaction_date is None else self.source_transaction_date.isoformat()

    @property
    def balance_display(self) -> str:
        return "" if self.balance_pence is None else _format_pence(self.balance_pence)


class BalanceObservation(models.Model):
    """A source-supported balance anchor for one account."""

    class Kind(models.TextChoices):
        OPENING = "opening", "Opening balance"
        CLOSING = "closing", "Closing balance"

    account = models.ForeignKey(
        Account, on_delete=models.PROTECT, related_name="balance_observations"
    )
    upload = models.ForeignKey(
        Upload, on_delete=models.PROTECT, related_name="balance_observations"
    )
    kind = models.CharField(max_length=20, choices=Kind.choices)
    # Only a source-evidenced date is recorded; a previous balance often has none.
    observed_on = models.DateField(null=True, blank=True)
    amount_pence = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["observed_on", "pk"]

    @property
    def amount_display(self) -> str:
        return _format_pence(self.amount_pence)

    @property
    def source_date_display(self) -> str:
        return "" if self.source_transaction_date is None else self.source_transaction_date.isoformat()


def _format_pence(amount_pence: int) -> str:
    sign = "-" if amount_pence < 0 else ""
    pence = abs(amount_pence)
    return f"{sign}£{pence // 100:,}.{pence % 100:02d}"


class Correction(models.Model):
    """A user-confirmed classification override with append-only history."""

    class Classification(models.TextChoices):
        SPENDING = "spending", "Spending"
        INCOME = "income", "Income"
        TRANSFER = "transfer", "Transfer between own accounts"
        REFUND = "refund", "Refund"
        UNKNOWN = "unknown", "Unknown"

    transaction = models.ForeignKey(
        Transaction, on_delete=models.CASCADE, related_name="corrections"
    )
    classification = models.CharField(max_length=20, choices=Classification.choices)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reverted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["pk"]

    @property
    def is_active(self) -> bool:
        return self.reverted_at is None


class DuplicateMatch(models.Model):
    """A user-confirmed duplicate relationship between two source rows.

    Both rows and their provenance remain; only the confirmed duplicate's
    reporting effect is suppressed.
    """

    transaction = models.ForeignKey(
        Transaction, on_delete=models.CASCADE, related_name="duplicate_matches"
    )
    duplicate_of = models.ForeignKey(
        Transaction, on_delete=models.CASCADE, related_name="duplicate_targets"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["transaction"], name="one_duplicate_decision")
        ]


class TransferLink(models.Model):
    """A user-confirmed relationship between two tracked-account entries.

    Both transactions and their provenance remain; the link changes reporting
    semantics only (a repayment is not spending, an own transfer is neither
    spending nor income nor external outgoing).
    """

    class Kind(models.TextChoices):
        TRANSFER = "transfer", "Own-account transfer"
        REPAYMENT = "repayment", "Card repayment"

    transaction_a = models.ForeignKey(
        Transaction, on_delete=models.CASCADE, related_name="transfer_links_a"
    )
    transaction_b = models.ForeignKey(
        Transaction, on_delete=models.CASCADE, related_name="transfer_links_b"
    )
    kind = models.CharField(max_length=20, choices=Kind.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["transaction_a"], name="one_link_for_a"),
            models.UniqueConstraint(fields=["transaction_b"], name="one_link_for_b"),
        ]


class ReversalLink(models.Model):
    """A user-confirmed reversal of an evidenced original charge or payment.

    The reversal row keeps its own source entry; only spending/income effects are
    reversed in the reversal's posting period. Gross cash outgoing is preserved.
    """

    transaction = models.OneToOneField(
        Transaction, on_delete=models.CASCADE, related_name="reversal_link"
    )
    reverses = models.ForeignKey(
        Transaction, on_delete=models.PROTECT, related_name="reversal_targets"
    )
    created_at = models.DateTimeField(auto_now_add=True)
