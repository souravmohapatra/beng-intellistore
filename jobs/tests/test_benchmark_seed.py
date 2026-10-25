"""Guards and behavior for the synthetic performance dataset seeder."""

import shutil
import tempfile

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from ledger.models import BalanceObservation, Transaction


class SeedBenchmarkTests(TestCase):
    def setUp(self):
        self.data_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.data_dir, ignore_errors=True)
        self.override = override_settings(DATA_DIR=self.data_dir)
        self.override.enable()
        self.addCleanup(self.override.disable)

    def test_requires_explicit_isolation_confirmation(self):
        with self.assertRaisesRegex(CommandError, "confirm-isolated"):
            call_command("seed_benchmark_data", transactions=10)
        self.assertEqual(Transaction.objects.count(), 0)

    def test_refuses_the_live_database_name(self):
        with self.assertRaisesRegex(CommandError, "Refusing to seed the live database"):
            call_command(
                "seed_benchmark_data",
                transactions=10,
                confirm_isolated=True,
                live_database="test_intellistore",
            )
        self.assertEqual(Transaction.objects.count(), 0)

    def test_seeds_an_isolated_dataset_once(self):
        call_command(
            "seed_benchmark_data", transactions=50, years=2, confirm_isolated=True
        )
        self.assertEqual(Transaction.objects.count(), 50)
        self.assertEqual(BalanceObservation.objects.count(), 2)

        call_command(
            "seed_benchmark_data", transactions=50, years=2, confirm_isolated=True
        )
        self.assertEqual(Transaction.objects.count(), 50)
