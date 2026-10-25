"""Behavioral browser-level checks for the dashboard totals."""

from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from ledger.models import Account, AccountKind, BalanceObservation
from reporting.tests.test_totals import add, make_upload


class DashboardTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="sourav", password="local-dev-password"
        )
        self.client.force_login(self.user)
        self.current = Account.objects.create(name="Current", kind=AccountKind.CURRENT)
        self.card = Account.objects.create(name="Card", kind=AccountKind.CARD)
        self.savings = Account.objects.create(name="Savings", kind=AccountKind.SAVINGS)
        self.upload_current = make_upload(self.current, "c")
        self.upload_card = make_upload(self.card, "d")
        self.upload_savings = make_upload(self.savings, "e")

        add(self.current, self.upload_current, date(2026, 8, 1), "SALARY ACME", "Salary", 250000)
        add(self.current, self.upload_current, date(2026, 8, 2), "RENT", "DD", -95000)
        add(self.current, self.upload_current, date(2026, 8, 3), "CASH", "Cash withdrawal", -10000)
        add(self.current, self.upload_current, date(2026, 8, 4), "REFUND", "Refund", 1244)
        add(self.card, self.upload_card, date(2026, 8, 5), "SHOP", "", 5000)
        add(self.savings, self.upload_savings, date(2026, 8, 7), "Gross Interest", "Interest", 10)

    def add_balances(self):
        for account, upload, amount in (
            (self.current, self.upload_current, 300000),
            (self.card, self.upload_card, 2000),
            (self.savings, self.upload_savings, 25030),
        ):
            BalanceObservation.objects.create(
                account=account,
                upload=upload,
                kind="closing",
                observed_on=date(2026, 8, 31),
                amount_pence=amount,
            )

    def test_dashboard_shows_posting_period_totals(self):
        self.add_balances()

        page = self.client.get("/")

        self.assertContains(page, "Spending")
        self.assertContains(page, "£1,087.56")
        self.assertContains(page, "£2,500.10")
        self.assertContains(page, "£1,050.00")
        self.assertContains(page, "£3,230.30")
        self.assertNotContains(page, "Provisional")

    def test_unresolved_classification_makes_totals_provisional(self):
        add(self.current, self.upload_current, date(2026, 8, 9), "To someone", "Others", -500)

        page = self.client.get("/")

        self.assertContains(page, "Provisional")
        self.assertContains(page, "1 transaction(s)")

    def test_missing_balance_evidence_is_stated_not_zeroed(self):
        page = self.client.get("/")

        self.assertContains(page, "Net cash is incomplete")
        self.assertContains(page, "Current")

class LeapDayTests(TestCase):
    def setUp(self):
        get_user_model().objects.create_user(username="sourav", password="local-dev-password")
        self.client.login(username="sourav", password="local-dev-password")

    def test_leap_day_default_period_is_calendar_safe(self):
        from unittest import mock

        from django.utils import timezone

        with mock.patch.object(timezone, "localdate", return_value=date(2028, 2, 29)):
            page = self.client.get("/")

        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "2027-03-01")
        self.assertContains(page, "2028-02-29")


class EmptyDashboardTests(TestCase):
    def setUp(self):
        get_user_model().objects.create_user(username="sourav", password="local-dev-password")
        self.client.login(username="sourav", password="local-dev-password")

    def test_empty_dashboard_does_not_fabricate_zero_totals(self):
        page = self.client.get("/")

        self.assertContains(page, "No reporting period has evidence yet")
        self.assertNotContains(page, "£0.00")
