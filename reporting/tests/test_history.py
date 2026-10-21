"""Behavioral tests for period selection and gap-aware history."""

from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from ledger.models import Account, AccountKind, BalanceObservation
from reporting.tests.test_totals import add, make_upload


class HistoryTestCase(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="sourav", password="local-dev-password"
        )
        self.client.force_login(self.user)
        self.current = Account.objects.create(name="Current", kind=AccountKind.CURRENT)
        self.card = Account.objects.create(name="Card", kind=AccountKind.CARD)
        self.savings = Account.objects.create(name="Savings", kind=AccountKind.SAVINGS)
        self.upload = make_upload(self.current, "current.pdf")
        add(self.current, self.upload, date(2026, 8, 1), "SALARY ACME", "Salary", 250000)
        add(self.current, self.upload, date(2026, 8, 2), "RENT", "DD", -95000)

    def observe(self, account, day, amount, kind="closing", upload=None):
        BalanceObservation.objects.create(
            account=account,
            upload=upload or self.upload,
            kind=kind,
            observed_on=day,
            amount_pence=amount,
        )


class PeriodSelectionTests(HistoryTestCase):
    def test_default_period_remains_trailing_twelve_months(self):
        page = self.client.get("/")

        self.assertContains(page, "Reporting period")
        self.assertContains(page, "2025-10-22")
        self.assertContains(page, "2026-10-21")

    def test_month_selection_updates_every_figure_and_bounds(self):
        page = self.client.get("/", {"month": "2026-08"})

        self.assertContains(page, "2026-08-01")
        self.assertContains(page, "2026-08-31")
        self.assertContains(page, "£950.00")

    def test_year_selection_is_supported(self):
        page = self.client.get("/", {"year": "2026"})

        self.assertContains(page, "2026-01-01")
        self.assertContains(page, "2026-12-31")

    def test_custom_range_excludes_outside_rows(self):
        page = self.client.get("/", {"start": "2026-08-02", "end": "2026-08-02"})

        self.assertContains(page, "2026-08-02")
        self.assertContains(page, "£950.00")
        self.assertNotContains(page, "£2,500.00")

    def test_invalid_range_falls_back_with_a_visible_message(self):
        page = self.client.get("/", {"start": "2026-09-01", "end": "2026-08-01"})

        self.assertContains(page, "not a valid period")
        self.assertContains(page, "2025-10-22")

    def test_older_history_remains_queryable(self):
        old_upload = make_upload(self.current, "old")
        add(self.current, old_upload, date(2024, 3, 5), "OLD RENT", "DD", -12345)

        page = self.client.get("/", {"start": "2024-03-01", "end": "2024-03-31"})

        self.assertContains(page, "£123.45")


class HistoryPointTests(HistoryTestCase):
    def test_points_exist_only_where_balance_evidence_exists(self):
        self.observe(self.current, date(2026, 8, 1), 100000, "opening")
        self.observe(self.current, date(2026, 8, 31), 105000)
        self.observe(self.card, date(2026, 8, 31), 5000)

        page = self.client.get("/", {"month": "2026-08"})

        self.assertContains(page, "Net-cash history")
        self.assertContains(page, "2026-08-01")
        self.assertContains(page, "£1,000.00")
        self.assertContains(page, "2026-08-31")
        self.assertContains(page, "£1,000.00")  # 1050.00 - 50.00 card debt
        self.assertContains(page, "current.pdf")  # balance source context
        self.assertContains(page, "only where balance evidence exists")

    def test_sparse_observations_are_points_not_daily_history(self):
        self.observe(self.savings, date(2026, 8, 10), 25000)
        self.observe(self.savings, date(2026, 8, 20), 25010)

        page = self.client.get("/", {"month": "2026-08"})

        self.assertContains(page, "2026-08-10")
        self.assertContains(page, "2026-08-20")
        self.assertNotContains(page, "2026-08-15")

    def test_long_gap_between_observations_is_reported(self):
        self.observe(self.current, date(2026, 1, 10), 100000)
        self.observe(self.current, date(2026, 8, 31), 105000)

        page = self.client.get("/", {"year": "2026"})

        self.assertContains(page, "Coverage gap")
        self.assertContains(page, "Current")

    def test_graph_plots_only_evidence_points_with_period_bounds(self):
        self.observe(self.savings, date(2026, 8, 10), 25000)
        self.observe(self.savings, date(2026, 8, 20), 25010)

        page = self.client.get("/", {"month": "2026-08"})

        self.assertContains(page, "<svg")
        self.assertEqual(page.content.decode().count("<circle"), 2)
        self.assertContains(page, "2026-08-01")
        self.assertContains(page, "2026-08-31")
        self.assertContains(page, "gaps are not interpolated")

    def test_graph_is_absent_without_evidence(self):
        page = self.client.get("/", {"month": "2026-08"})

        self.assertNotContains(page, "<svg")

    def test_conflicting_same_date_balances_are_disputed(self):
        self.observe(self.current, date(2026, 8, 31), 100000)
        self.observe(self.current, date(2026, 8, 31), 90000)

        page = self.client.get("/", {"month": "2026-08"})

        self.assertContains(page, "Disputed")
        self.assertContains(page, "conflicting observations")
        self.assertContains(page, "Disputed balance evidence for")
        self.assertContains(page, "excluded from net cash")

    def test_account_without_observations_is_named(self):
        page = self.client.get("/", {"month": "2026-08"})

        self.assertContains(page, "no balance evidence")
        self.assertContains(page, "Savings")
