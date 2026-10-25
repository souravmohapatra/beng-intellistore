"""Seed a synthetic benchmark dataset into an *isolated* database only.

Never run this against live data. The command refuses the configured live
database name and requires an explicit confirmation flag.
"""

from datetime import date, timedelta
import hashlib
from pathlib import Path
import random

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from ledger.models import Account, AccountKind, BalanceObservation, Original, Transaction, Upload


class Command(BaseCommand):
    help = "Create synthetic accounts/transactions for performance measurement."

    def add_arguments(self, parser):
        parser.add_argument("--transactions", type=int, default=100_000)
        parser.add_argument("--years", type=int, default=10)
        parser.add_argument("--confirm-isolated", action="store_true")
        parser.add_argument("--live-database", default="intellistore")

    def handle(self, *args, **options):
        database = settings.DATABASES["default"]["NAME"]
        if not options["confirm_isolated"]:
            raise CommandError(
                "Pass --confirm-isolated after verifying this is not live data."
            )
        if database == options["live_database"]:
            raise CommandError(
                f"Refusing to seed the live database {database!r}; use an isolated copy."
            )
        if options["transactions"] < 1 or options["years"] < 1:
            raise CommandError("transactions and years must be positive")

        account, _ = Account.objects.get_or_create(
            name="Benchmark current", defaults={"kind": AccountKind.CURRENT}
        )
        payload = b"synthetic benchmark original\n"
        digest = hashlib.sha256(payload).hexdigest()
        stored = Path("originals") / digest[:2] / digest
        path = Path(settings.DATA_DIR) / stored
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_bytes(payload)
        original, _ = Original.objects.get_or_create(
            sha256=digest,
            defaults={
                "stored_path": str(stored),
                "byte_size": len(payload),
                "content_type": "text/plain",
            },
        )
        upload, _ = Upload.objects.get_or_create(
            original=original,
            account=account,
            filename="benchmark-synthetic.txt",
        )
        if Transaction.objects.filter(upload=upload).exists():
            self.stdout.write(
                f"Benchmark data already present: "
                f"{Transaction.objects.filter(upload=upload).count()} transactions"
            )
            return

        random.seed(20261025)
        end = date(2026, 10, 25)
        start = end - timedelta(days=365 * options["years"] + options["years"] // 4)
        span = (end - start).days
        rows = []
        for index in range(options["transactions"]):
            posted = start + timedelta(days=(index * span) // options["transactions"])
            amount = -random.randint(100, 25000)
            rows.append(
                Transaction(
                    account=account,
                    upload=upload,
                    posted_on=posted,
                    description=f"SYNTHETIC MERCHANT {index % 5000:04d}",
                    transaction_type="Card payment",
                    amount_pence=amount,
                    balance_pence=None,
                    source_page=1,
                    source_row=index + 1,
                    source_text=f"Synthetic benchmark row {index + 1}",
                )
            )
        Transaction.objects.bulk_create(rows, batch_size=2000)
        for kind, observed in (("opening", start), ("closing", end)):
            BalanceObservation.objects.create(
                account=account,
                upload=upload,
                kind=kind,
                observed_on=observed,
                amount_pence=1_000_000 if kind == "opening" else 1_000_000 - 500_000,
            )
        self.stdout.write(
            f"Seeded {len(rows)} transactions from {start} to {end} in {database!r}"
        )
